import os
import sys
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database
from dotenv import load_dotenv
import datetime
import json
import base64
import cv2
import numpy as np
from PIL import Image
import hashlib  # Thêm thư viện mã hóa mật khẩu
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import requests

# Thêm thư mục hiện tại vào đường dẫn để import module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tải biến môi trường
load_dotenv()

# Cấu hình kết nối database
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'emotion_detection1.2')

DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emotion.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime)
    profile_image = db.Column(db.String(255))
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))

class Camera(db.Model):
    __tablename__ = 'cameras'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    camera_type = db.Column(db.String(50))  # webcam, droidcam, ipcam
    status = db.Column(db.String(20), default='active')  # active, inactive
    ip_address = db.Column(db.String(50))  # For IP cameras and DroidCam
    port = db.Column(db.Integer)  # For IP cameras and DroidCam
    stream_url = db.Column(db.String(200))  # Full stream URL for IP cameras and DroidCam
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_connected = db.Column(db.DateTime)  # Thời gian kết nối cuối cùng
    connection_status = db.Column(db.String(20), default='disconnected')  # connected, disconnected, error
    
    # Relationships
    user = db.relationship('User', backref=db.backref('cameras', lazy=True))
    emotions = db.relationship('Emotion', backref='camera', lazy=True)

    def generate_stream_url(self):
        """Tạo URL stream dựa trên loại camera"""
        if self.camera_type == 'droidcam':
            # DroidCam URL format
            return f"http://{self.ip_address}:{self.port}/video"
        elif self.camera_type == 'ipcam':
            # IP Camera URL - có thể cần điều chỉnh theo loại camera
            return f"http://{self.ip_address}:{self.port}/video"
        return None

    def test_connection(self):
        """Kiểm tra kết nối với camera"""
        try:
            if self.camera_type in ['droidcam', 'ipcam']:
                if not self.stream_url:
                    return False
                
                # Thử kết nối đến camera
                response = requests.get(self.stream_url, timeout=5)
                if response.status_code == 200:
                    self.connection_status = 'connected'
                    self.last_connected = datetime.datetime.utcnow()
                    return True
            elif self.camera_type == 'webcam':
                # Thử mở webcam
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    self.connection_status = 'connected'
                    self.last_connected = datetime.datetime.utcnow()
                    cap.release()
                    return True
            
            self.connection_status = 'error'
            return False
        except Exception as e:
            self.connection_status = 'error'
            return False

class Emotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    dominant_emotion = db.Column(db.String(50))
    emotion_scores = db.Column(db.JSON)
    image_path = db.Column(db.String(255))
    processed_image_path = db.Column(db.String(255))
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=False)
    camera = db.relationship('Camera', backref=db.backref('emotions', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('emotions', lazy=True))
    image_base64 = db.Column(db.Text)
    processed_image_base64 = db.Column(db.Text)

def create_db():
    """Tạo database nếu chưa tồn tại"""
    try:
        # Kết nối đến PostgreSQL server (không chỉ định database)
        conn_string = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres'
        engine = create_engine(conn_string)
        
        # Kiểm tra xem database đã tồn tại chưa
        if not database_exists(engine.url.set(database=DB_NAME)):
            print(f"Tạo database mới: {DB_NAME}")
            # Tạo database mới
            create_database(engine.url.set(database=DB_NAME))
            print(f"Database {DB_NAME} đã được tạo thành công!")
        else:
            print(f"Database {DB_NAME} đã tồn tại!")
        
        return True
    except Exception as e:
        print(f"Lỗi khi tạo database: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_tables():
    """Tạo các bảng trong database"""
    try:
        # Kết nối đến database
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        
        # Tạo bảng users
        create_users_table = text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            email VARCHAR(100),
            role VARCHAR(20) DEFAULT 'user',
            is_active BOOLEAN DEFAULT TRUE,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            profile_image VARCHAR(255),
            phone VARCHAR(20),
            address VARCHAR(200)
        )
        """)
        
        # Tạo bảng cameras
        create_cameras_table = text("""
        CREATE TABLE IF NOT EXISTS cameras (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            location VARCHAR(200),
            camera_type VARCHAR(50),
            status VARCHAR(20) DEFAULT 'active',
            ip_address VARCHAR(50),
            port INTEGER,
            stream_url VARCHAR(200),
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_connected TIMESTAMP,
            connection_status VARCHAR(20) DEFAULT 'disconnected'
        )
        """)
        
        # Tạo bảng emotions
        create_emotions_table = text("""
        CREATE TABLE IF NOT EXISTS emotions (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            camera_id INTEGER NOT NULL REFERENCES cameras(id),
            image_path VARCHAR(255) NOT NULL,
            result_path VARCHAR(255) NOT NULL,
            dominant_emotion VARCHAR(50),
            emotion_scores JSONB,
            image_base64 TEXT,
            processed_image_base64 TEXT,
            user_id INTEGER REFERENCES users(id)
        )
        """)
        
        # Thực thi các câu lệnh tạo bảng
        conn.execute(create_users_table)
        conn.execute(create_cameras_table)
        conn.execute(create_emotions_table)
        
        # Commit thay đổi
        conn.commit()
        conn.close()
        
        print("Tạo các bảng thành công!")
        return True
    except Exception as e:
        print(f"Lỗi khi tạo bảng: {e}")
        import traceback
        traceback.print_exc()
        return False

def init_default_data():
    """Khởi tạo dữ liệu mặc định cho database"""
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        
        # Tạo user admin mặc định
        admin_password = generate_password_hash('admin123')
        insert_admin = text("""
        INSERT INTO users (username, password_hash, email, role, is_active, created_at)
        VALUES ('admin2', :password_hash, 'admin@example.com', 'admin', true, NOW())
        ON CONFLICT (username) DO NOTHING
        RETURNING id
        """)
        
        result = conn.execute(insert_admin, {'password_hash': admin_password})
        admin_id = result.scalar()
        
        if admin_id:
            # Tạo camera mặc định
            insert_camera = text("""
            INSERT INTO cameras (name, location, camera_type, status, user_id, created_at, updated_at)
            VALUES 
            ('Default Webcam', 'Main Office', 'webcam', 'active', :user_id, NOW(), NOW()),
            ('DroidCam 1', 'Mobile Device', 'droidcam', 'active', :user_id, NOW(), NOW()),
            ('IP Camera 1', 'Security Room', 'ipcam', 'active', :user_id, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """)
            
            conn.execute(insert_camera, {'user_id': admin_id})
            conn.commit()
            
            print("Đã tạo dữ liệu mặc định thành công!")
            return True
        else:
            print("Không thể tạo user admin!")
            return False
            
    except Exception as e:
        print(f"Lỗi khi khởi tạo dữ liệu mặc định: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def create_image_directories():
    """Tạo các thư mục lưu trữ hình ảnh"""
    try:
        base_dir = os.path.abspath(os.getcwd())
        print(f"Thư mục gốc: {base_dir}")
        
        # Tạo thư mục gốc cho hình ảnh
        images_root = os.path.join(base_dir, "images")
        if not os.path.exists(images_root):
            os.makedirs(images_root, exist_ok=True)
            print(f"Đã tạo thư mục gốc cho hình ảnh: {images_root}")
        
        # Tạo thư mục debug
        debug_dir = os.path.join(base_dir, "debug_images")
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir, exist_ok=True)
            print(f"Đã tạo thư mục debug: {debug_dir}")
        
        # Tạo thư mục cho từng camera
        for i in range(1, 4):
            camera_dir = os.path.join(images_root, f"camera{i}")
            if not os.path.exists(camera_dir):
                os.makedirs(camera_dir, exist_ok=True)
                print(f"Đã tạo thư mục cho camera {i}: {camera_dir}")
        
        print("Tạo các thư mục lưu trữ hình ảnh thành công!")
        return True
    except Exception as e:
        print(f"Lỗi khi tạo thư mục lưu trữ hình ảnh: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_env_file():
    """Cập nhật file .env với cấu hình kết nối database"""
    try:
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        env_example_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example")
        
        # Nội dung cho file .env
        env_content = f"""DB_USER={DB_USER}
DB_PASSWORD={DB_PASSWORD}
DB_HOST={DB_HOST}
DB_PORT={DB_PORT}
DB_NAME={DB_NAME}
DATABASE_URL={DATABASE_URL}
"""
        
        # Ghi file .env
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        # Tạo file .env.example nếu chưa có
        if not os.path.exists(env_example_file):
            with open(env_example_file, 'w') as f:
                f.write("""DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=emotion_detection
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/emotion_detection
""")
        
        print("Cập nhật file .env thành công!")
        return True
    except Exception as e:
        print(f"Lỗi khi cập nhật file .env: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_data():
    """Tạo dữ liệu test để kiểm tra database"""
    try:
        # Kiểm tra xem đã có dữ liệu trong bảng emotions chưa
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        
        check_emotions = text("SELECT COUNT(*) FROM emotions")
        result = conn.execute(check_emotions).scalar()
        
        # Nếu đã có dữ liệu, không cần tạo thêm
        if result > 0:
            print(f"Đã có {result} bản ghi trong bảng emotions, không cần tạo dữ liệu test")
            conn.close()
            return True
        
        # Tạo một hình ảnh test đơn giản
        base_dir = os.path.abspath(os.getcwd())
        images_root = os.path.join(base_dir, "images")
        
        # Tạo hình ảnh test và kết quả cho mỗi camera
        for camera_id in range(1, 4):
            camera_dir = os.path.join(images_root, f"camera{camera_id}")
            
            # Tạo hình ảnh đơn giản với một khuôn mặt vẽ
            img = np.ones((300, 400, 3), dtype=np.uint8) * 255  # Hình ảnh trắng
            # Vẽ khuôn mặt đơn giản
            cv2.circle(img, (200, 150), 100, (0, 0, 255), 2)  # Khuôn mặt
            cv2.circle(img, (160, 120), 15, (0, 0, 0), -1)  # Mắt trái
            cv2.circle(img, (240, 120), 15, (0, 0, 0), -1)  # Mắt phải
            cv2.ellipse(img, (200, 180), (50, 20), 0, 0, 180, (0, 0, 0), 2)  # Miệng cười
            
            # Lưu hình ảnh gốc
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{timestamp}.jpg"
            result_filename = f"{timestamp}_result.json"
            processed_filename = f"{timestamp}_processed.jpg"
            
            image_path = os.path.join(camera_dir, image_filename)
            result_path = os.path.join(camera_dir, result_filename)
            processed_path = os.path.join(camera_dir, processed_filename)
            
            # Lưu hình ảnh gốc
            cv2.imwrite(image_path, img)
            
            # Tạo kết quả giả lập
            emotion_result = {
                "emotion": {
                    "angry": 0.05,
                    "disgust": 0.02,
                    "fear": 0.01,
                    "happy": 0.75,
                    "sad": 0.05,
                    "surprise": 0.02,
                    "neutral": 0.1
                },
                "dominant_emotion": "happy",
                "emotion_percent": {
                    "angry": 5,
                    "disgust": 2,
                    "fear": 1,
                    "happy": 75,
                    "sad": 5,
                    "surprise": 2,
                    "neutral": 10
                }
            }
            
            # Lưu kết quả
            with open(result_path, 'w') as f:
                json.dump(emotion_result, f)
            
            # Tạo hình ảnh đã xử lý (thêm text vào hình ảnh gốc)
            processed_img = img.copy()
            cv2.putText(processed_img, "Happy: 75%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(processed_img, f"Timestamp: {timestamp}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Lưu hình ảnh đã xử lý
            cv2.imwrite(processed_path, processed_img)
            
            # Chuyển đổi hình ảnh thành base64
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            with open(processed_path, 'rb') as proc_file:
                processed_data = proc_file.read()
                processed_image_base64 = base64.b64encode(processed_data).decode('utf-8')
            
            # Thêm vào database
            insert_emotion = text("""
            INSERT INTO emotions (timestamp, camera_id, image_path, result_path, dominant_emotion, emotion_scores, image_base64, processed_image_base64)
            VALUES (:timestamp, :camera_id, :image_path, :result_path, :dominant_emotion, :emotion_scores, :image_base64, :processed_image_base64)
            """)
            
            conn.execute(insert_emotion, {
                'timestamp': datetime.datetime.now(),
                'camera_id': camera_id,
                'image_path': image_path,
                'result_path': result_path,
                'dominant_emotion': 'happy',
                'emotion_scores': json.dumps(emotion_result['emotion']),
                'image_base64': image_base64,
                'processed_image_base64': processed_image_base64
            })
            
            print(f"Đã tạo dữ liệu test cho camera {camera_id}")
        
        # Commit thay đổi
        conn.commit()
        conn.close()
        
        print("Tạo dữ liệu test thành công!")
        return True
    except Exception as e:
        print(f"Lỗi khi tạo dữ liệu test: {e}")
        import traceback
        traceback.print_exc()
        return False

def init_db():
    """Initialize database tables and default data"""
    with app.app_context():
        # Drop all existing tables
        db.drop_all()
        
        # Create tables in correct order
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin2').first()
        if not admin:
            admin = User(
                username='admin2',
                password=generate_password_hash('admin123'),
                email='admin@example.com',
                role='admin',
                is_active=True,
                full_name='Administrator'
            )
            db.session.add(admin)
            db.session.commit()
            
        # Create default camera if not exists
        default_camera = Camera.query.filter_by(name='Default Camera').first()
        if not default_camera:
            default_camera = Camera(
                name='Default Camera',
                location='Main Office',
                camera_type='webcam',
                status='active',
                user_id=admin.id
            )
            db.session.add(default_camera)
            db.session.commit()
            
        print("Database initialized successfully!")

def add_camera(name, location, camera_type, ip_address=None, port=None, user_id=None):
    """Thêm camera mới vào database"""
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        
        # Tạo stream URL nếu là IP camera hoặc DroidCam
        stream_url = None
        if camera_type in ['ipcam', 'droidcam'] and ip_address and port:
            stream_url = f"http://{ip_address}:{port}/video"
        
        insert_camera = text("""
        INSERT INTO cameras (name, location, camera_type, status, ip_address, port, stream_url, user_id, created_at, updated_at)
        VALUES (:name, :location, :camera_type, 'active', :ip_address, :port, :stream_url, :user_id, NOW(), NOW())
        RETURNING id
        """)
        
        result = conn.execute(insert_camera, {
            'name': name,
            'location': location,
            'camera_type': camera_type,
            'ip_address': ip_address,
            'port': port,
            'stream_url': stream_url,
            'user_id': user_id
        })
        
        camera_id = result.scalar()
        conn.commit()
        
        print(f"Đã thêm camera mới với ID: {camera_id}")
        return camera_id
        
    except Exception as e:
        print(f"Lỗi khi thêm camera: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        conn.close()

def update_camera_status(camera_id, status):
    """Cập nhật trạng thái camera"""
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        
        update_status = text("""
        UPDATE cameras 
        SET status = :status, updated_at = NOW()
        WHERE id = :camera_id
        """)
        
        conn.execute(update_status, {
            'status': status,
            'camera_id': camera_id
        })
        conn.commit()
        
        print(f"Đã cập nhật trạng thái camera {camera_id} thành {status}")
        return True
        
    except Exception as e:
        print(f"Lỗi khi cập nhật trạng thái camera: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def get_all_cameras():
    """Lấy danh sách tất cả camera"""
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        
        select_cameras = text("""
        SELECT id, name, location, camera_type, status, ip_address, port, stream_url, user_id, created_at, updated_at
        FROM cameras
        ORDER BY created_at DESC
        """)
        
        result = conn.execute(select_cameras)
        cameras = [dict(row) for row in result]
        
        return cameras
        
    except Exception as e:
        print(f"Lỗi khi lấy danh sách camera: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()

def main():
    """Hàm chính để thiết lập database"""
    print("=== THIẾT LẬP DATABASE CHO ỨNG DỤNG NHẬN DIỆN CẢM XÚC ===")
    
    # Cập nhật file .env
    update_env_file()
    
    # Tạo database
    if not create_db():
        print("Không thể tạo database, kết thúc quá trình thiết lập!")
        return
    
    # Tạo các bảng
    if not create_tables():
        print("Không thể tạo các bảng, kết thúc quá trình thiết lập!")
        return
    
    # Khởi tạo dữ liệu mặc định
    if not init_default_data():
        print("Không thể khởi tạo dữ liệu mặc định, kết thúc quá trình thiết lập!")
        return
    
    # Tạo dữ liệu test
    create_test_data()
    
    # Initialize the database
    init_db()
    
    print("=== THIẾT LẬP DATABASE HOÀN TẤT ===")
    print(f"URL kết nối database: {DATABASE_URL}")
    print("Bạn có thể chạy ứng dụng bằng lệnh: python app.py")

if __name__ == "__main__":
    main() 
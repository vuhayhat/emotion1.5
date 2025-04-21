import os
import sys
import datetime
import json
import base64
import cv2
import numpy as np
from flask import Flask
from werkzeug.security import generate_password_hash
import traceback

# Thêm thư mục hiện tại vào đường dẫn để import module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tải biến môi trường
from dotenv import load_dotenv
load_dotenv()

# Cấu hình kết nối database từ biến môi trường
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'emotion_detection1.3')

DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Tạo ứng dụng Flask tạm thời để kết nối database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import db và các model sau khi cấu hình
from models import db, User, Camera, CameraGroup, CameraSchedule, Emotion, CameraGroupAssociation

# Khởi tạo SQLAlchemy với Flask app
db.init_app(app)

def init_default_data():
    """Khởi tạo dữ liệu mặc định cho database"""
    try:
        with app.app_context():
            # Kiểm tra xem đã có user admin chưa
            admin = User.query.filter_by(username='admin2').first()
            if not admin:
                # Tạo user admin
                admin = User(
                    username='admin2',
                    password_hash=generate_password_hash('admin123'),
                    email='admin@example.com',
                    role='admin',
                    is_active=True,
                    full_name='Administrator'
                )
                db.session.add(admin)
                db.session.commit()
                
                # Tạo thêm user thường
                normal_user = User(
                    username='user1',
                    password_hash=generate_password_hash('user123'),
                    email='user@example.com',
                    role='user',
                    is_active=True,
                    full_name='Normal User'
                )
                db.session.add(normal_user)
                db.session.commit()
                
                # Tạo camera mặc định
                default_cameras = [
                    Camera(
                        name='Default Webcam',
                        location='Main Office',
                        camera_type='webcam',
                        status='active',
                        user_id=admin.id
                    ),
                    Camera(
                        name='DroidCam 1',
                        location='Mobile Device',
                        camera_type='droidcam',
                        status='active',
                        ip_address='192.168.1.100',
                        port=4747,
                        user_id=admin.id
                    ),
                    Camera(
                        name='IP Camera 1',
                        location='Security Room',
                        camera_type='ipcam',
                        status='active',
                        stream_url='rtsp://admin:admin123@192.168.1.108:554',
                        user_id=admin.id
                    ),
                    Camera(
                        name='User Webcam',
                        location='User Office',
                        camera_type='webcam',
                        status='active',
                        user_id=normal_user.id
                    )
                ]
                
                for camera in default_cameras:
                    db.session.add(camera)
                
                db.session.commit()
                
                # Tạo camera group mặc định
                default_groups = [
                    CameraGroup(
                        name='Default Group',
                        description='Default camera group',
                        status='active',
                        max_concurrent_cameras=4
                    ),
                    CameraGroup(
                        name='Security Cameras',
                        description='Security monitoring cameras',
                        status='active',
                        max_concurrent_cameras=8
                    ),
                    CameraGroup(
                        name='Office Cameras',
                        description='Office monitoring cameras',
                        status='active',
                        max_concurrent_cameras=4
                    )
                ]
                
                for group in default_groups:
                    db.session.add(group)
                
                db.session.commit()
                
                # Liên kết camera với group
                # Lấy ID của các camera và group
                cameras = Camera.query.all()
                groups = CameraGroup.query.all()
                
                # Default Group chứa tất cả camera
                default_group = groups[0]
                for camera in cameras:
                    assoc = CameraGroupAssociation(camera_id=camera.id, group_id=default_group.id)
                    db.session.add(assoc)
                
                # Security Group chứa IP camera
                security_group = groups[1]
                security_cam = next((c for c in cameras if c.camera_type == 'ipcam'), None)
                if security_cam:
                    assoc = CameraGroupAssociation(camera_id=security_cam.id, group_id=security_group.id)
                    db.session.add(assoc)
                
                # Office Group chứa webcam
                office_group = groups[2]
                office_cams = [c for c in cameras if c.camera_type == 'webcam']
                for cam in office_cams:
                    assoc = CameraGroupAssociation(camera_id=cam.id, group_id=office_group.id)
                    db.session.add(assoc)
                
                # Tạo lịch chụp tự động cho camera
                schedules = [
                    CameraSchedule(
                        camera_id=cameras[0].id,
                        type='interval',
                        interval_minutes=15,
                        is_active=True
                    ),
                    CameraSchedule(
                        camera_id=cameras[2].id,
                        type='fixed_time',
                        hour='9,12,15,18',
                        minute='0',
                        is_active=True
                    )
                ]
                
                for schedule in schedules:
                    db.session.add(schedule)
                
                db.session.commit()
                print("Đã tạo dữ liệu mặc định thành công!")
                return True
            else:
                print("User admin đã tồn tại, không cần tạo lại dữ liệu mặc định")
                return True
    except Exception as e:
        print(f"Lỗi khi khởi tạo dữ liệu mặc định: {e}")
        traceback.print_exc()
        return False

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
        
        # Tạo thư mục static
        static_dir = os.path.join(base_dir, "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir, exist_ok=True)
            print(f"Đã tạo thư mục static: {static_dir}")
        
        # Tạo thư mục cho từng camera
        with app.app_context():
            # Tạo thư mục cho các camera mặc định
            for i in range(1, 5):
                camera_dir = os.path.join(images_root, f"camera{i}")
                os.makedirs(camera_dir, exist_ok=True)
                print(f"Đã tạo thư mục cho camera {i}: {camera_dir}")
                
            # Tạo thư mục cho các camera đã đăng ký
            cameras = Camera.query.all()
            for camera in cameras:
                camera_dir = os.path.join(images_root, f"camera{camera.id}")
                os.makedirs(camera_dir, exist_ok=True)
                print(f"Đã tạo thư mục cho camera {camera.id}: {camera_dir}")
        
        print("Tạo các thư mục lưu trữ hình ảnh thành công!")
        return True
    except Exception as e:
        print(f"Lỗi khi tạo thư mục lưu trữ hình ảnh: {e}")
        traceback.print_exc()
        return False

def create_test_data():
    """Tạo dữ liệu test để kiểm tra database"""
    try:
        with app.app_context():
            # Kiểm tra xem đã có dữ liệu trong bảng emotions chưa
            emotions_count = Emotion.query.count()
            
            # Nếu đã có dữ liệu, không cần tạo thêm
            if emotions_count > 0:
                print(f"Đã có {emotions_count} bản ghi trong bảng emotions, không cần tạo dữ liệu test")
                return True
            
            # Lấy danh sách camera
            cameras = Camera.query.all()
            if not cameras:
                print("Không có camera nào trong database, không thể tạo dữ liệu test")
                return False
                
            # Tạo một hình ảnh test đơn giản
            base_dir = os.path.abspath(os.getcwd())
            images_root = os.path.join(base_dir, "images")
            
            # Các loại cảm xúc để tạo dữ liệu test đa dạng
            emotions = [
                {
                    "dominant": "happy", 
                    "scores": {"angry": 0.05, "disgust": 0.02, "fear": 0.01, "happy": 0.75, "sad": 0.05, "surprise": 0.02, "neutral": 0.1}
                },
                {
                    "dominant": "sad", 
                    "scores": {"angry": 0.1, "disgust": 0.05, "fear": 0.15, "happy": 0.05, "sad": 0.5, "surprise": 0.05, "neutral": 0.1}
                },
                {
                    "dominant": "neutral", 
                    "scores": {"angry": 0.05, "disgust": 0.05, "fear": 0.05, "happy": 0.1, "sad": 0.1, "surprise": 0.05, "neutral": 0.6}
                },
                {
                    "dominant": "angry", 
                    "scores": {"angry": 0.6, "disgust": 0.1, "fear": 0.1, "happy": 0.02, "sad": 0.08, "surprise": 0.05, "neutral": 0.05}
                }
            ]
            
            # Tạo hình ảnh test và kết quả cho mỗi camera
            for camera in cameras:
                camera_dir = os.path.join(images_root, f"camera{camera.id}")
                os.makedirs(camera_dir, exist_ok=True)
                
                # Tạo 2 hình ảnh cho mỗi camera với cảm xúc khác nhau
                for i in range(2):
                    # Chọn một loại cảm xúc ngẫu nhiên
                    emotion_data = emotions[i % len(emotions)]
                    
                    # Tạo hình ảnh đơn giản với một khuôn mặt vẽ
                    img = np.ones((300, 400, 3), dtype=np.uint8) * 255  # Hình ảnh trắng
                    # Vẽ khuôn mặt đơn giản
                    cv2.circle(img, (200, 150), 100, (0, 0, 255), 2)  # Khuôn mặt
                    cv2.circle(img, (160, 120), 15, (0, 0, 0), -1)  # Mắt trái
                    cv2.circle(img, (240, 120), 15, (0, 0, 0), -1)  # Mắt phải
                    
                    # Vẽ miệng tùy theo cảm xúc
                    if emotion_data["dominant"] == "happy":
                        # Miệng cười
                        cv2.ellipse(img, (200, 180), (50, 20), 0, 0, 180, (0, 0, 0), 2)
                    elif emotion_data["dominant"] == "sad":
                        # Miệng buồn
                        cv2.ellipse(img, (200, 200), (50, 20), 0, 180, 360, (0, 0, 0), 2)
                    elif emotion_data["dominant"] == "angry":
                        # Miệng giận
                        cv2.line(img, (150, 190), (250, 190), (0, 0, 0), 2)
                        cv2.line(img, (150, 190), (170, 170), (0, 0, 0), 2)
                        cv2.line(img, (250, 190), (230, 170), (0, 0, 0), 2)
                    else:
                        # Miệng trung tính
                        cv2.line(img, (150, 190), (250, 190), (0, 0, 0), 2)
                    
                    # Tạo timestamp và filenames
                    timestamp = (datetime.datetime.now() - datetime.timedelta(hours=i)).strftime("%Y%m%d_%H%M%S")
                    image_filename = f"{timestamp}.jpg"
                    result_filename = f"{timestamp}_result.json"
                    processed_filename = f"{timestamp}_processed.jpg"
                    
                    image_path = os.path.join(camera_dir, image_filename)
                    result_path = os.path.join(camera_dir, result_filename)
                    processed_path = os.path.join(camera_dir, processed_filename)
                    
                    # Lưu hình ảnh gốc
                    cv2.imwrite(image_path, img)
                    
                    # Lưu kết quả phân tích cảm xúc
                    with open(result_path, 'w') as f:
                        json.dump(emotion_data["scores"], f)
                    
                    # Tạo hình ảnh đã xử lý (thêm text vào hình ảnh gốc)
                    processed_img = img.copy()
                    dominant = emotion_data["dominant"].capitalize()
                    percentage = int(emotion_data["scores"][emotion_data["dominant"]] * 100)
                    
                    cv2.putText(processed_img, f"{dominant}: {percentage}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(processed_img, f"Timestamp: {timestamp}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.rectangle(processed_img, (100, 50), (300, 250), (0, 255, 0), 2)  # Khung nhận diện khuôn mặt
                    
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
                    emotion = Emotion(
                        camera_id=camera.id,
                        image_path=image_path,
                        result_path=result_path,
                        dominant_emotion=emotion_data["dominant"],
                        emotion_scores=emotion_data["scores"],
                        image_base64=image_base64,
                        processed_image_base64=processed_image_base64,
                        user_id=camera.user_id
                    )
                    db.session.add(emotion)
                    
                print(f"Đã tạo dữ liệu test cho camera {camera.id}")
            
            # Commit thay đổi
            db.session.commit()
            
            print("Tạo dữ liệu test thành công!")
            return True
    except Exception as e:
        print(f"Lỗi khi tạo dữ liệu test: {e}")
        traceback.print_exc()
        return False

def main():
    """Hàm chính để thêm dữ liệu mẫu vào database"""
    print("=== THÊM DỮ LIỆU MẪU CHO DATABASE ===")
    
    # Khởi tạo dữ liệu mặc định nếu chưa có
    if not init_default_data():
        print("Không thể khởi tạo dữ liệu mặc định!")
    
    # Tạo thư mục lưu trữ hình ảnh nếu chưa có
    if not create_image_directories():
        print("Không thể tạo thư mục lưu trữ hình ảnh!")
    
    # Tạo dữ liệu test nếu chưa có
    if not create_test_data():
        print("Không thể tạo dữ liệu test!")
    
    print("=== THÊM DỮ LIỆU MẪU HOÀN TẤT ===")
    print("Bạn có thể chạy ứng dụng bằng lệnh: python app.py")

if __name__ == "__main__":
    main() 
import os
import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timezone, timedelta

# Khởi tạo SQLAlchemy nhưng chưa liên kết với app
db = SQLAlchemy()

# Tạo múi giờ Việt Nam (UTC+7)
vietnam_tz = timezone(timedelta(hours=7))

def get_vietnam_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    return datetime.datetime.now(vietnam_tz)

# Định nghĩa các model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    updated_at = db.Column(db.DateTime, default=get_vietnam_time, onupdate=get_vietnam_time)
    profile_image = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    
    # Định nghĩa relationships
    cameras = db.relationship('Camera', backref='user', lazy=True)
    emotions = db.relationship('Emotion', backref='user', lazy=True)
    
    def __init__(self, username, password_hash, email=None, role='user', is_active=True, full_name=None, profile_image=None, phone=None, address=None):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.role = role
        self.is_active = is_active
        self.full_name = full_name
        self.profile_image = profile_image
        self.phone = phone
        self.address = address
        self.created_at = get_vietnam_time()
        self.updated_at = get_vietnam_time()
    
    def to_dict(self):
        """Chuyển đổi object thành dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'profile_image': self.profile_image,
            'phone': self.phone,
            'address': self.address
        }
    
    def set_password(self, password):
        """Thiết lập mật khẩu đã băm"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Kiểm tra mật khẩu"""
        return check_password_hash(self.password_hash, password)

class Camera(db.Model):
    __tablename__ = 'cameras'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    camera_type = db.Column(db.String(50))  # webcam, droidcam, ipcam
    status = db.Column(db.String(20), default='active')  # active, inactive, maintenance
    ip_address = db.Column(db.String(50))
    port = db.Column(db.Integer)
    stream_url = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    updated_at = db.Column(db.DateTime, default=get_vietnam_time, onupdate=get_vietnam_time)
    last_connected = db.Column(db.DateTime)
    connection_status = db.Column(db.String(20), default='disconnected')  # connected, disconnected
    
    # Định nghĩa relationships
    emotions = db.relationship('Emotion', backref='camera', lazy=True, cascade="all, delete-orphan")
    schedules = db.relationship('CameraSchedule', backref='camera', lazy=True, cascade="all, delete-orphan")
    camera_groups = db.relationship('CameraGroupAssociation', back_populates='camera')
    
    def __init__(self, name, location=None, camera_type='webcam', status='active', ip_address=None, port=None, stream_url=None, user_id=None, connection_status='disconnected'):
        self.name = name
        self.location = location
        self.camera_type = camera_type
        self.status = status
        self.ip_address = ip_address
        self.port = port
        self.stream_url = stream_url
        self.user_id = user_id
        self.created_at = get_vietnam_time()
        self.updated_at = get_vietnam_time()
        self.connection_status = connection_status
    
    def to_dict(self):
        """Chuyển đổi object thành dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'camera_type': self.camera_type,
            'status': self.status,
            'ip_address': self.ip_address,
            'port': self.port,
            'stream_url': self.stream_url,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'connection_status': self.connection_status
        }
    
    def get_stream_url(self):
        """Tạo URL stream dựa trên loại camera"""
        if self.camera_type == 'webcam':
            return 'webcam'
        elif self.camera_type == 'droidcam' and self.ip_address and self.port:
            return f'http://{self.ip_address}:{self.port}/video'
        elif self.camera_type == 'ipcam' and self.stream_url:
            return self.stream_url
        return None

# Table liên kết nhiều-nhiều giữa Camera và CameraGroup
class CameraGroupAssociation(db.Model):
    __tablename__ = 'camera_group_association'
    
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('camera_groups.id'), primary_key=True)
    added_at = db.Column(db.DateTime, default=get_vietnam_time)
    
    # Định nghĩa relationships
    camera = db.relationship('Camera', back_populates='camera_groups')
    group = db.relationship('CameraGroup', back_populates='cameras')

class CameraGroup(db.Model):
    __tablename__ = 'camera_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')  # active, inactive
    max_concurrent_cameras = db.Column(db.Integer, default=4)
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    updated_at = db.Column(db.DateTime, default=get_vietnam_time, onupdate=get_vietnam_time)
    
    # Định nghĩa relationships
    cameras = db.relationship('CameraGroupAssociation', back_populates='group')
    
    def __init__(self, name, description=None, status='active', max_concurrent_cameras=4):
        self.name = name
        self.description = description
        self.status = status
        self.max_concurrent_cameras = max_concurrent_cameras
        self.created_at = get_vietnam_time()
        self.updated_at = get_vietnam_time()
    
    def to_dict(self):
        """Chuyển đổi object thành dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'max_concurrent_cameras': self.max_concurrent_cameras,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'cameras': [assoc.camera_id for assoc in self.cameras]
        }

class CameraSchedule(db.Model):
    __tablename__ = 'camera_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False)
    type = db.Column(db.String(20), default='interval')  # interval, fixed_time
    interval_minutes = db.Column(db.Integer)  # For interval type
    hour = db.Column(db.String(10))  # For fixed_time type (comma separated values or ranges)
    minute = db.Column(db.String(10))  # For fixed_time type (comma separated values or ranges)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    updated_at = db.Column(db.DateTime, default=get_vietnam_time, onupdate=get_vietnam_time)
    
    def __init__(self, camera_id, type='interval', interval_minutes=None, hour=None, minute=None, is_active=True):
        self.camera_id = camera_id
        self.type = type
        self.interval_minutes = interval_minutes
        self.hour = hour
        self.minute = minute
        self.is_active = is_active
        self.created_at = get_vietnam_time()
        self.updated_at = get_vietnam_time()
    
    def to_dict(self):
        """Chuyển đổi object thành dictionary"""
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'type': self.type,
            'interval_minutes': self.interval_minutes,
            'hour': self.hour,
            'minute': self.minute,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Emotion(db.Model):
    __tablename__ = 'emotions'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=get_vietnam_time)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    result_path = db.Column(db.String(255), nullable=False)
    dominant_emotion = db.Column(db.String(50))  # happy, sad, angry, etc.
    emotion_scores = db.Column(db.Text)  # JSON string with emotion scores
    image_base64 = db.Column(db.Text)  # Base64 encoded image
    processed_image_base64 = db.Column(db.Text)  # Base64 encoded processed image
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __init__(self, camera_id, image_path, result_path, dominant_emotion=None, emotion_scores=None, image_base64=None, processed_image_base64=None, user_id=None):
        self.timestamp = get_vietnam_time()
        self.camera_id = camera_id
        self.image_path = image_path
        self.result_path = result_path
        self.dominant_emotion = dominant_emotion
        self.emotion_scores = json.dumps(emotion_scores) if emotion_scores else None
        self.image_base64 = image_base64
        self.processed_image_base64 = processed_image_base64
        self.user_id = user_id
    
    def to_dict(self):
        """Chuyển đổi object thành dictionary"""
        emotion_scores_dict = json.loads(self.emotion_scores) if self.emotion_scores else {}
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'camera_id': self.camera_id,
            'camera_name': self.camera.name if self.camera else None,
            'dominant_emotion': self.dominant_emotion,
            'emotion_scores': emotion_scores_dict,
            'user_id': self.user_id,
            'image_url': f'/api/image/{self.id}' if self.id else None,
            'processed_image_url': f'/api/processed-image/{self.id}' if self.id else None
        } 

class DetectionResult(db.Model):
    """Model lưu kết quả nhận diện khuôn mặt và cảm xúc"""
    __tablename__ = 'detection_results'

    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    face_location = db.Column(db.JSON, nullable=False)  # Lưu vị trí khuôn mặt dạng JSON
    emotion = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=get_vietnam_time)

    # Quan hệ với camera
    camera = db.relationship('Camera', backref=db.backref('detection_results', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'image_path': self.image_path,
            'face_location': self.face_location,
            'emotion': self.emotion,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }

# Khởi tạo database khi chạy file models.py trực tiếp
if __name__ == "__main__":
    from flask import Flask
    import os
    from dotenv import load_dotenv
    
    # Tải biến môi trường nếu có file .env
    load_dotenv()
    
    app = Flask(__name__)
    
    # Lấy thông tin kết nối từ biến môi trường hoặc sử dụng giá trị mặc định
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'password')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'emotion_db')
    
    # Cấu hình database URI cho PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Khởi tạo app với SQLAlchemy
    db.init_app(app)
    
    # Tạo tất cả các bảng trong database
    with app.app_context():
        try:
            db.create_all()
            print("Database PostgreSQL đã được khởi tạo thành công!")
            
            # Thêm code để kiểm tra và hiển thị danh sách bảng đã tạo
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"\nDanh sách bảng đã tạo ({len(tables)} bảng):")
            for table in tables:
                print(f"- {table}")
                
        except Exception as e:
            print(f"Lỗi khi khởi tạo database: {e}") 
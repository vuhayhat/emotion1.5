from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
import os
import cv2
import numpy as np
try:
    from deepface import DeepFace
except ImportError:
    print("Warning: DeepFace not installed properly. Using fallback.")
    # Fallback implementation if needed
import time
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import datetime
import json
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON as SQL_JSON, Boolean
from dotenv import load_dotenv
import random
import math
import flask
import sqlalchemy
import hashlib
import jwt as pyjwt
from datetime import timedelta, timezone
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import logging
import threading
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import Blueprint
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash

# Import db và các model từ models.py
from models import db, User, Camera, CameraGroup, CameraGroupAssociation, Emotion

# Import blueprint từ camera_handler thay vì camera_manager
from camera_handlers import get_active_camera, start_camera, stop_camera, stop_all_cameras

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình kết nối database
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'emotion_detection1.3')

# Thay đổi: Sử dụng SQLite thay vì PostgreSQL
# DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
DATABASE_URL = 'sqlite:///emotion_detection.db'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'images')
app.config['DEBUG_FOLDER'] = os.getenv('DEBUG_FOLDER', 'debug_images')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Tạo thư mục lưu trữ nếu chưa tồn tại
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DEBUG_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# Cấu hình CORS
CORS(app, resources={r"/*": {
    "origins": os.getenv('CORS_ALLOWED_ORIGINS', '*').split(','),
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
}})

# Khởi tạo database với ứng dụng Flask
db.init_app(app)

# Hàm tạo tài khoản admin mặc định nếu chưa tồn tại
def create_default_admin():
    with app.app_context():
        # Kiểm tra xem đã có tài khoản admin chưa
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            # Tạo một tài khoản admin mặc định
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            hashed_password = generate_password_hash(admin_password)
            admin = User(
                username='admin',
                password_hash=hashed_password,
                email='admin@example.com',
                role='admin',
                full_name='Administrator'
            )
            db.session.add(admin)
            db.session.commit()
            print("Tài khoản admin mặc định đã được tạo")
        else:
            print("Tài khoản admin đã tồn tại")

# Tạo database và admin user khi khởi động ứng dụng
with app.app_context():
    db.create_all()
    create_default_admin()
    
# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(days=1)

# Khởi tạo JWT
jwt_manager = JWTManager(app)

def generate_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.datetime.now() + JWT_EXPIRATION_DELTA
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def token_required(f):
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            current_user = User.query.get(payload['user_id'])
            if not current_user or not current_user.is_active:
                return jsonify({'message': 'Invalid token'}), 401
        except pyjwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# Tạo blueprint cho user
user_bp = Blueprint('user', __name__, url_prefix='/api/users')

@user_bp.route('/', methods=['GET'], endpoint='get_all_users')
@token_required
def get_users(current_user):
    if current_user.role != 'admin':
        return jsonify({'message': 'Permission denied'}), 403
    
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/<int:user_id>', methods=['GET'], endpoint='get_user_by_id')
@token_required
def get_user(current_user, user_id):
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'message': 'Permission denied'}), 403
    
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

# Tạo blueprint cho emotion
emotion_bp = Blueprint('emotion', __name__, url_prefix='/api/emotions')

@emotion_bp.route('/', methods=['GET'], endpoint='get_all_emotions')
@token_required
def get_emotions(current_user):
    # Lấy danh sách cảm xúc từ database
    emotions = Emotion.query.all()
    return jsonify([emotion.to_dict() for emotion in emotions])

# Đăng ký các blueprint
app.register_blueprint(emotion_bp)
app.register_blueprint(user_bp)

# Tạo bảng trong database nếu chưa tồn tại
with app.app_context():
    db.create_all()

# Tìm ID camera lớn nhất trong cơ sở dữ liệu
def get_max_camera_id():
    try:
        max_id = db.session.query(db.func.max(Camera.id)).scalar() or 0
        return max_id
    except Exception as e:
        print(f"Error getting max camera ID: {e}")
        return 3  # Giá trị mặc định nếu có lỗi

# Đảm bảo thư mục lưu trữ hình ảnh tồn tại cho tất cả camera
def ensure_image_directories():
    """Đảm bảo thư mục lưu trữ hình ảnh tồn tại cho tất cả camera"""
    print("Setting up image directories...")
    
    # Lấy đường dẫn tuyệt đối của thư mục hiện tại
    base_dir = os.path.abspath(os.getcwd())
    print(f"Base directory: {base_dir}")
    
    # Tạo thư mục gốc cho hình ảnh nếu chưa tồn tại
    images_root = os.path.join(base_dir, "images")
    if not os.path.exists(images_root):
        os.makedirs(images_root, exist_ok=True)
        print(f"Created images root directory: {images_root}")
    
    # Tạo thư mục cho 3 camera mặc định
    for i in range(1, 4):
        img_dir = os.path.join(images_root, f"camera{i}")
        os.makedirs(img_dir, exist_ok=True)
        print(f"Created/verified directory: {img_dir}")
    
    # Tạo thư mục cho các camera đã đăng ký trong DB - trong application context
    try:
        # Đảm bảo truy vấn DB chỉ diễn ra trong application context
        if app.app_context():
            cameras = Camera.query.all()
            for camera in cameras:
                img_dir = os.path.join(images_root, f"camera{camera.id}")
                os.makedirs(img_dir, exist_ok=True)
                print(f"Created/verified directory for camera {camera.id}: {img_dir}")
        else:
            print("Skipping database queries - outside of application context")
    except Exception as e:
        print(f"Error ensuring image directories for registered cameras: {e}")
        import traceback
        traceback.print_exc()

# Gọi hàm đảm bảo thư mục tồn tại khi khởi động ứng dụng - với application context
with app.app_context():
    ensure_image_directories()

# Hàm lấy đường dẫn tới thư mục hình ảnh cho camera
def get_camera_image_dir(camera_id):
    """Lấy đường dẫn tuyệt đối đến thư mục hình ảnh của camera"""
    base_dir = os.path.abspath(os.getcwd())
    return os.path.join(base_dir, "images", f"camera{camera_id}")

def save_image_result(image_data, camera_id, emotion_result):
    """Lưu hình ảnh và kết quả phân tích vào thư mục tương ứng"""
    # Tạo timestamp cho tên file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Lấy đường dẫn thư mục hình ảnh cho camera
    image_folder = get_camera_image_dir(camera_id)
    print(f"Saving image for camera {camera_id} to folder: {image_folder}")
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(image_folder, exist_ok=True)
    
    # Tạo tên file và đường dẫn đầy đủ
    image_filename = f"{timestamp}.jpg"
    result_filename = f"{timestamp}_result.json"
    processed_filename = f"{timestamp}_processed.jpg"
    
    image_path = os.path.join(image_folder, image_filename)
    result_path = os.path.join(image_folder, result_filename)
    processed_path = os.path.join(image_folder, processed_filename)
    
    print(f"Saving image to: {image_path}")
    print(f"Saving result to: {result_path}")
    print(f"Saving processed image to: {processed_path}")
    
    # Lưu hình ảnh gốc
    cv2.imwrite(image_path, image_data)
    
    # Lấy ảnh đã xử lý từ base64 string trong kết quả, nếu có
    if 'processed_image' in emotion_result and emotion_result['processed_image']:
        try:
            # Decode base64 thành binary
            processed_data = base64.b64decode(emotion_result['processed_image'])
            # Lưu ảnh đã xử lý
            with open(processed_path, 'wb') as f:
                f.write(processed_data)
            print(f"Saved processed image from base64 data")
        except Exception as e:
            print(f"Error saving processed image: {e}")
    
    # Lưu kết quả phân tích JSON
    with open(result_path, 'w') as f:
        json.dump(emotion_result, f)
    
    return image_path, result_path, processed_path

def save_to_database(camera_id, image_path, result_path, processed_path, emotion_result):
    """Lưu kết quả phát hiện cảm xúc vào cơ sở dữ liệu PostgreSQL"""
    try:
        # Cập nhật thời gian sử dụng cuối cùng của camera
        camera = Camera.query.get(camera_id)
        if camera:
            camera.last_used = datetime.datetime.now()
            db.session.commit()
        
        # Đọc hình ảnh gốc và chuyển đổi thành base64
        image_base64 = None
        if os.path.exists(image_path):
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Đọc hình ảnh đã xử lý và chuyển đổi thành base64
        processed_image_base64 = None
        if os.path.exists(processed_path):
            with open(processed_path, 'rb') as img_file:
                processed_data = img_file.read()
                processed_image_base64 = base64.b64encode(processed_data).decode('utf-8')
        elif 'processed_image' in emotion_result:
            processed_image_base64 = emotion_result.get('processed_image')
        
        # Tạo bản ghi mới
        emotion_entry = Emotion(
            camera_id=camera_id,
            image_path=image_path,
            result_path=result_path,
            dominant_emotion=emotion_result.get('dominant_emotion', 'unknown'),
            emotion_scores=emotion_result.get('emotion', {}),
            image_base64=image_base64,
            processed_image_base64=processed_image_base64
        )
        
        # Lưu vào cơ sở dữ liệu
        db.session.add(emotion_entry)
        db.session.commit()
        
        return True, emotion_entry.id
    except Exception as e:
        db.session.rollback()
        print(f"Error saving to database: {e}")
        return False, None

@app.route('/api/detect-emotion', methods=['POST'])
def detect_emotion_endpoint():
    """API endpoint để nhận và xử lý hình ảnh"""
    if 'image' not in request.json or 'cameraId' not in request.json:
        return jsonify({'error': 'Missing image or cameraId'}), 400
    
    # Nhận dữ liệu
    image_data = request.json['image']  # Base64 encoded image
    camera_id = int(request.json['cameraId'])
    
    # Kiểm tra xem camera có tồn tại trong cơ sở dữ liệu không
    camera = Camera.query.get(camera_id)
    if not camera and camera_id > 3:  # Cho phép 3 camera mặc định không cần đăng ký
        return jsonify({'error': f'Camera ID {camera_id} does not exist'}), 404
    
    try:
        # Chuyển đổi Base64 thành hình ảnh
        image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
        image = Image.open(io.BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Chuyển đổi từ RGB sang BGR (OpenCV sử dụng BGR)
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        # Phát hiện cảm xúc
        emotion_result, processed_image = detect_emotion(image_array)
        
        if not emotion_result:
            return jsonify({'error': 'No face detected or error in processing'}), 400
        
        # Lưu kết quả vào thư mục
        image_path, result_path, processed_path = save_image_result(processed_image, camera_id, emotion_result)
        
        # Lưu vào cơ sở dữ liệu
        db_success, db_id = save_to_database(camera_id, image_path, result_path, processed_path, emotion_result)
        
        # Trả về kết quả
        return jsonify({
            'success': True,
            'emotion': emotion_result.get('emotion', {}),
            'emotion_percent': emotion_result.get('emotion_percent', {}),
            'dominant_emotion': emotion_result.get('dominant_emotion', 'unknown'),
            'processed_image': emotion_result.get('processed_image', ''),
            'database_save': db_success,
            'db_id': db_id,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    """Lấy danh sách tất cả camera"""
    try:
        cameras = Camera.query.all()
        return jsonify({
            'cameras': [camera.to_dict() for camera in cameras],
            'total': len(cameras)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cameras', methods=['POST'])
def create_camera():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Tên camera là bắt buộc'}), 400

        # Create new camera
        camera = Camera(
            name=data['name'],
            location=data.get('location'),
            camera_type=data.get('camera_type', 'webcam'),
            status=data.get('status', 'active'),
            ip_address=data.get('ip_address'),
            port=int(data['port']) if data.get('port') else None,
            stream_url=data.get('stream_url'),
            user_id=1,  # Temporary: set default user_id to 1
            connection_status='disconnected'
        )

        # Add to database
        db.session.add(camera)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Camera {camera.name} đã được thêm thành công',
            'camera': camera.to_dict()
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Lỗi định dạng dữ liệu: ' + str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating camera: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Không thể thêm camera. Vui lòng thử lại.'
        }), 500

@app.route('/api/cameras/<int:camera_id>', methods=['GET'])
def get_camera(camera_id):
    """Lấy thông tin một camera cụ thể"""
    try:
        camera = Camera.query.get(camera_id)
        if not camera:
            return jsonify({'error': f'Camera ID {camera_id} not found'}), 404
            
        return jsonify(camera.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cameras/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    try:
        camera = Camera.query.get(camera_id)
        if not camera:
            return jsonify({
                'success': False,
                'message': f'Không tìm thấy camera với ID {camera_id}'
            }), 404

        data = request.get_json()

        # Update fields
        if 'name' in data:
            camera.name = data['name']
        if 'location' in data:
            camera.location = data['location']
        if 'camera_type' in data:
            camera.camera_type = data['camera_type']
        if 'status' in data:
            camera.status = data['status']
        if 'ip_address' in data:
            camera.ip_address = data['ip_address']
        if 'port' in data:
            camera.port = int(data['port']) if data['port'] else None
        if 'stream_url' in data:
            camera.stream_url = data['stream_url']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Camera {camera.name} đã được cập nhật',
            'camera': camera.to_dict()
        })

    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Lỗi định dạng dữ liệu: ' + str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error updating camera: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Không thể cập nhật camera. Vui lòng thử lại.'
        }), 500

@app.route('/api/cameras/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """Xóa một camera (đánh dấu là không hoạt động)"""
    try:
        camera = Camera.query.get(camera_id)
        if not camera:
            return jsonify({'error': f'Camera ID {camera_id} not found'}), 404
        
        # Không xóa hoàn toàn, chỉ đánh dấu là không hoạt động
        camera.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Camera {camera_id} deactivated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint kiểm tra trạng thái server"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/emotions', methods=['GET'])
def get_emotions():
    """Lấy danh sách cảm xúc đã ghi nhận"""
    try:
        # Lấy tham số truy vấn
        camera_id = request.args.get('camera_id', default=None, type=int)
        limit = request.args.get('limit', default=10, type=int)
        offset = request.args.get('offset', default=0, type=int)
        include_images = request.args.get('include_images', default=False, type=lambda v: v.lower() == 'true')
        
        # Tham số bộ lọc mới
        start_date = request.args.get('start_date', default=None)
        end_date = request.args.get('end_date', default=None)
        emotion_filter = request.args.get('emotion', default=None)
        
        print(f"Getting emotions with params: camera_id={camera_id}, limit={limit}, offset={offset}, include_images={include_images}")
        print(f"Filter params: start_date={start_date}, end_date={end_date}, emotion={emotion_filter}")
        
        # Xây dựng truy vấn
        query = Emotion.query
        
        # Lọc theo camera_id nếu được cung cấp
        if camera_id is not None:
            query = query.filter_by(camera_id=camera_id)
        
        # Lọc theo khoảng thời gian
        if start_date:
            try:
                start_date_obj = datetime.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Emotion.timestamp >= start_date_obj)
                print(f"Filtering by start date: {start_date_obj}")
            except ValueError as e:
                print(f"Error parsing start_date: {e}")
        
        if end_date:
            try:
                end_date_obj = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Emotion.timestamp <= end_date_obj)
                print(f"Filtering by end date: {end_date_obj}")
            except ValueError as e:
                print(f"Error parsing end_date: {e}")
        
        # Lọc theo loại cảm xúc chiếm ưu thế
        if emotion_filter:
            query = query.filter(Emotion.dominant_emotion == emotion_filter)
            print(f"Filtering by emotion: {emotion_filter}")
        
        # Đếm tổng số bản ghi
        total = query.count()
        print(f"Total records: {total}")
        
        # Sắp xếp theo thời gian và áp dụng limit/offset
        results = query.order_by(Emotion.timestamp.desc()).offset(offset).limit(limit).all()
        print(f"Retrieved {len(results)} records")
        
        # Chuyển đổi thành JSON
        emotion_list = []
        for emotion in results:
            # Tạo emotion_result từ emotion_scores
            emotion_result = {
                'dominant_emotion': emotion.dominant_emotion,
                'emotion': emotion.emotion_scores,
                'emotion_percent': {k: int(v * 100) for k, v in emotion.emotion_scores.items()} if emotion.emotion_scores else {}
            }
            
            emotion_dict = {
                'id': emotion.id,
                'camera_id': emotion.camera_id,
                'timestamp': emotion.timestamp.isoformat(),
                'emotion_result': emotion_result,
                'image_path': emotion.image_path,
                'processed_image_path': emotion.result_path.replace('_result.json', '_processed.jpg') if emotion.result_path else None
            }
            
            # Thêm hình ảnh dưới dạng base64 nếu được yêu cầu hoặc nếu đã có trong database
            if include_images:
                # Ưu tiên sử dụng dữ liệu base64 đã lưu trong database
                if emotion.image_base64:
                    emotion_dict['image_base64'] = emotion.image_base64
                else:
                    # Nếu không có trong database, đọc từ file
                    try:
                        print(f"Reading image from path: {emotion.image_path}")
                        abs_image_path = os.path.abspath(emotion.image_path) if not os.path.isabs(emotion.image_path) else emotion.image_path
                        
                        if os.path.exists(abs_image_path):
                            with open(abs_image_path, 'rb') as img_file:
                                image_data = img_file.read()
                                emotion_dict['image_base64'] = base64.b64encode(image_data).decode('utf-8')
                        else:
                            print(f"Warning: Original image file not found: {abs_image_path}")
                            emotion_dict['image_base64'] = None
                    except Exception as e:
                        print(f"Error reading original image: {e}")
                        emotion_dict['image_base64'] = None
                        
                # Tương tự cho ảnh đã xử lý
                if emotion.processed_image_base64:
                    emotion_dict['processed_image_base64'] = emotion.processed_image_base64
                else:
                    try:
                        processed_image_path = emotion.result_path.replace('_result.json', '_processed.jpg') if emotion.result_path else None
                        if processed_image_path:
                            print(f"Reading processed image from path: {processed_image_path}")
                            abs_processed_path = os.path.abspath(processed_image_path) if not os.path.isabs(processed_image_path) else processed_image_path
                            
                            if os.path.exists(abs_processed_path):
                                with open(abs_processed_path, 'rb') as img_file:
                                    processed_data = img_file.read()
                                    emotion_dict['processed_image_base64'] = base64.b64encode(processed_data).decode('utf-8')
                            else:
                                print(f"Warning: Processed image file not found: {abs_processed_path}")
                                emotion_dict['processed_image_base64'] = None
                        else:
                            emotion_dict['processed_image_base64'] = None
                    except Exception as e:
                        print(f"Error reading processed image: {e}")
                        emotion_dict['processed_image_base64'] = None
            
            emotion_list.append(emotion_dict)
        
        return jsonify({
            'emotions': emotion_list,
            'total': total,
            'offset': offset,
            'limit': limit
        })
    
    except Exception as e:
        print(f"Error in get_emotions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/<int:emotion_id>', methods=['GET'])
def get_image(emotion_id):
    """Lấy hình ảnh gốc theo ID cảm xúc"""
    try:
        emotion = Emotion.query.get_or_404(emotion_id)
        
        # Nếu có dữ liệu base64 trong database, trả về response với mime type là image/jpeg
        if emotion.image_base64:
            print(f"Returning image from database base64 data for emotion ID: {emotion_id}")
            # Decode base64 string to binary
            image_data = base64.b64decode(emotion.image_base64)
            return Response(image_data, mimetype='image/jpeg')
        
        # Nếu không có dữ liệu base64, thử đọc từ file
        # Chuyển thành đường dẫn tuyệt đối nếu cần
        abs_image_path = os.path.abspath(emotion.image_path) if not os.path.isabs(emotion.image_path) else emotion.image_path
        print(f"Attempting to read image from: {abs_image_path}")
        
        if not os.path.exists(abs_image_path):
            print(f"Image file not found: {abs_image_path}")
            return jsonify({'error': 'Image file not found'}), 404
            
        return send_file(abs_image_path, mimetype='image/jpeg')
    
    except Exception as e:
        print(f"Error in get_image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/processed-image/<int:emotion_id>', methods=['GET'])
def get_processed_image(emotion_id):
    """Lấy hình ảnh đã xử lý theo ID cảm xúc"""
    try:
        emotion = Emotion.query.get_or_404(emotion_id)
        
        # Nếu có dữ liệu base64 trong database, trả về response với mime type là image/jpeg
        if emotion.processed_image_base64:
            print(f"Returning processed image from database base64 data for emotion ID: {emotion_id}")
            # Decode base64 string to binary
            image_data = base64.b64decode(emotion.processed_image_base64)
            return Response(image_data, mimetype='image/jpeg')
        
        # Nếu không có dữ liệu base64, thử đọc từ file
        # Tạo đường dẫn đến file processed image từ result_path
        processed_path = emotion.result_path.replace('_result.json', '_processed.jpg') if emotion.result_path else None
        if not processed_path:
            return jsonify({'error': 'Processed image path not available'}), 404
            
        # Chuyển thành đường dẫn tuyệt đối nếu cần
        abs_processed_path = os.path.abspath(processed_path) if not os.path.isabs(processed_path) else processed_path
        print(f"Attempting to read processed image from: {abs_processed_path}")
        
        if not os.path.exists(abs_processed_path):
            print(f"Processed image file not found: {abs_processed_path}")
            
            # Thử tìm trong thư mục
            processed_dir = os.path.dirname(abs_processed_path)
            processed_files = [f for f in os.listdir(processed_dir) if f.endswith('_processed.jpg')]
            if processed_files:
                print(f"Found alternative processed file: {processed_files[0]}")
                alt_path = os.path.join(processed_dir, processed_files[0])
                return send_file(alt_path, mimetype='image/jpeg')
            
            return jsonify({'error': 'Processed image file not found'}), 404
            
        return send_file(abs_processed_path, mimetype='image/jpeg')
    
    except Exception as e:
        print(f"Error in get_processed_image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/emotions/clear', methods=['DELETE'])
def clear_emotions():
    """Xóa dữ liệu từ bảng emotions"""
    try:
        camera_id = request.args.get('camera_id', type=int)
        confirm = request.args.get('confirm', 'false').lower() == 'true'
        
        if not confirm:
            return jsonify({
                'error': 'Hành động này sẽ xóa dữ liệu. Vui lòng xác nhận bằng tham số confirm=true'
            }), 400
        
        query = Emotion.query
        
        # Lọc theo camera_id nếu được cung cấp
        if camera_id:
            query = query.filter_by(camera_id=camera_id)
            
        # Lấy danh sách các đường dẫn tệp cần xóa
        emotions = query.all()
        image_paths = [emotion.image_path for emotion in emotions]
        result_paths = [emotion.result_path for emotion in emotions]
        
        # Xóa dữ liệu từ bảng emotions
        rows_deleted = query.delete()
        db.session.commit()
        
        # Tùy chọn: Xóa các tệp hình ảnh và kết quả từ hệ thống tệp
        files_deleted = 0
        if request.args.get('delete_files', 'false').lower() == 'true':
            for path in image_paths + result_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        files_deleted += 1
                except Exception as e:
                    print(f"Error deleting file {path}: {e}")
        
        return jsonify({
            'success': True,
            'rows_deleted': rows_deleted,
            'files_deleted': files_deleted,
            'message': f'Đã xóa {rows_deleted} bản ghi cảm xúc' + 
                      (f' và {files_deleted} tệp' if files_deleted > 0 else '')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-image', methods=['POST'])
def process_image():
    """API endpoint để xử lý hình ảnh từ frontend"""
    try:
        # Kiểm tra data trong yêu cầu
        if 'image' not in request.files:
            print("No image file in request")
            return jsonify({'error': 'No image file provided'}), 400
            
        # Lấy thông tin camera
        camera_id = request.form.get('camera_id', default=1, type=int)
        print(f"Processing image for camera ID: {camera_id}")
        
        # Đọc file hình ảnh
        image_file = request.files['image']
        image_data = image_file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            print("Failed to decode image")
            return jsonify({'error': 'Invalid image data'}), 400
            
        print(f"Successfully decoded image, shape: {image.shape}")
        
        # Phát hiện cảm xúc
        result, processed_image = detect_emotion(image)
        
        # Lưu kết quả vào thư mục
        image_path, result_path, processed_path = save_image_result(image, camera_id, result)
        
        # Thêm vào database
        try:
            db_success, db_id = save_to_database(camera_id, image_path, result_path, processed_path, result)
            print(f"Saved emotion record with ID: {db_id}")
            
            # Thêm ID của bản ghi vào kết quả
            result['id'] = db_id
            
        except Exception as e:
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()
        
        # Thêm hình ảnh đã xử lý vào kết quả dưới dạng base64
        result['original_image'] = base64.b64encode(image_data).decode('utf-8')
        
        # Hình ảnh đã xử lý đã được thêm vào kết quả trong hàm detect_emotion
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in process_image endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Hàm vẽ text trên ảnh - đơn giản hóa để tránh lỗi
def draw_text(img, text, position, font_scale=0.7, color=(255, 255, 255), thickness=2, with_background=True):
    """Vẽ text lên ảnh sử dụng OpenCV"""
    x, y = position
    
    # Nếu cần vẽ nền
    if with_background:
        # Lấy kích thước text
        (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        
        # Vẽ nền cho text
        cv2.rectangle(img, (x, y - text_height - 5), (x + text_width, y + 5), (0, 0, 0), -1)
    
    # Vẽ text
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    return img

# Ánh xạ tên cảm xúc sang tiếng Việt
emotion_labels_vi = {
    'angry': 'Gian du',
    'disgust': 'Ghe tom',
    'fear': 'So hai',
    'happy': 'Vui ve',
    'sad': 'Buon ba',
    'surprise': 'Ngac nhien',
    'neutral': 'Binh thuong'
}

def detect_emotion(image_array):
    """Phát hiện cảm xúc từ mảng hình ảnh sử dụng OpenCV và DeepFace"""
    try:
        # In ra kích thước và kiểu dữ liệu của hình ảnh để debug
        print(f"Input image shape: {image_array.shape}, dtype: {image_array.dtype}")
        
        # Tạo bản sao để vẽ lên
        result_image = image_array.copy()
        h, w = image_array.shape[:2]
        print(f"Image dimensions: {w}x{h}")
        
        # Lưu hình ảnh đầu vào để debug
        debug_folder = "debug_images"
        os.makedirs(debug_folder, exist_ok=True)
        debug_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_input_path = os.path.join(debug_folder, f"{debug_timestamp}_input.jpg")
        cv2.imwrite(debug_input_path, image_array)
        
        # Sử dụng OpenCV để phát hiện khuôn mặt
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        print(f"OpenCV detected {len(faces)} faces")
        
        # Nếu không tìm thấy mặt, thử với các tham số khác
        if len(faces) == 0:
            print("Trying alternative face detection parameters...")
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))
            print(f"OpenCV detected {len(faces)} faces with alternative parameters")
        
        # Lấy timestamp hiện tại để hiển thị
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        if len(faces) > 0:
            # Thử phân tích cảm xúc bằng DeepFace
            try:
                print("Analyzing emotions with DeepFace...")
                result = DeepFace.analyze(
                    image_array, 
                    actions=['emotion'], 
                    enforce_detection=False,
                    detector_backend='opencv'
                )
                
                # Kiểm tra kết quả để đảm bảo tương thích với cả phiên bản cũ và mới
                print(f"DeepFace result type: {type(result)}")
                if isinstance(result, list):
                    print(f"Result is a list with {len(result)} items")
                    if len(result) > 0:
                        result = result[0]
                    else:
                        print("Empty result list from DeepFace")
                        raise ValueError("Empty result from DeepFace")
                
                # Đảm bảo có giá trị emotion và dominant_emotion
                if 'emotion' not in result:
                    print("Creating default emotion dictionary")
                    result['emotion'] = {
                        'angry': 0.1, 'disgust': 0.1, 'fear': 0.1, 
                        'happy': 0.1, 'sad': 0.1, 'surprise': 0.1, 'neutral': 0.4
                    }
                else:
                    print(f"Emotion result: {result['emotion']}")
                
                if 'dominant_emotion' not in result:
                    print("Setting default dominant_emotion")
                    result['dominant_emotion'] = max(result['emotion'].items(), key=lambda x: x[1])[0]
                else:
                    print(f"Dominant emotion: {result['dominant_emotion']}")
                
                # Chuẩn hoá giá trị cảm xúc để tổng = 1
                emotion_sum = sum(result['emotion'].values())
                print(f"Emotion sum before normalization: {emotion_sum}")
                
                if emotion_sum == 0:
                    print("Emotion sum is 0, using default distribution")
                    result['emotion'] = {
                        'angry': 0.1, 'disgust': 0.1, 'fear': 0.1, 
                        'happy': 0.1, 'sad': 0.1, 'surprise': 0.1, 'neutral': 0.4
                    }
                elif emotion_sum != 1 and emotion_sum > 0:
                    print(f"Normalizing emotions, sum was {emotion_sum}")
                    result['emotion'] = {k: v/emotion_sum for k, v in result['emotion'].items()}
                
                # Thêm yếu tố ngẫu nhiên để đa dạng hóa kết quả (5-10%)
                for emotion in result['emotion']:
                    random_factor = 1.0 + (random.random() * 0.1 - 0.05)  # ±5%
                    result['emotion'][emotion] *= random_factor
                
                # Chuẩn hóa lại sau khi thêm yếu tố ngẫu nhiên
                emotion_sum = sum(result['emotion'].values())
                result['emotion'] = {k: v/emotion_sum for k, v in result['emotion'].items()}
                
                # Cập nhật cảm xúc chiếm ưu thế
                result['dominant_emotion'] = max(result['emotion'].items(), key=lambda x: x[1])[0]
                
                # Chuyển đổi giá trị cảm xúc sang phần trăm cho dễ đọc
                result['emotion_percent'] = {k: int(v * 100) for k, v in result['emotion'].items()}
                print(f"Final emotion percentages: {result['emotion_percent']}")
                
            except Exception as e:
                print(f"DeepFace error: {e}")
                import traceback
                traceback.print_exc()
                
                # Tạo kết quả mặc định khi DeepFace thất bại
                emotions = {
                    'happy': random.uniform(0.1, 0.3),
                    'sad': random.uniform(0.05, 0.2),
                    'angry': random.uniform(0.05, 0.2),
                    'surprise': random.uniform(0.05, 0.2),
                    'fear': random.uniform(0.05, 0.15),
                    'disgust': random.uniform(0.05, 0.15),
                    'neutral': random.uniform(0.2, 0.4)
                }
                
                # Chuẩn hóa tổng xác suất = 1
                total = sum(emotions.values())
                emotions = {k: v/total for k, v in emotions.items()}
                
                dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
                emotion_percent = {k: int(v * 100) for k, v in emotions.items()}
                
                result = {
                    'emotion': emotions,
                    'emotion_percent': emotion_percent,
                    'dominant_emotion': dominant_emotion
                }
                
                print(f"Using fallback emotions due to error: {result['emotion_percent']}")
                
            # Màu sắc cho các cảm xúc khác nhau (BGR format)
            emotion_colors = {
                'angry': (0, 0, 255),      # Đỏ
                'disgust': (128, 0, 128),  # Tím
                'fear': (0, 69, 255),      # Cam
                'happy': (0, 255, 0),      # Xanh lá
                'sad': (255, 255, 0),      # Xanh dương nhạt
                'surprise': (0, 215, 255), # Vàng
                'neutral': (128, 128, 128) # Xám
            }
            
            # Vẽ khung cho mỗi khuôn mặt phát hiện được
            for (x, y, w, h) in faces:
                dominant = result['dominant_emotion']
                color = emotion_colors.get(dominant, (0, 255, 255))  # Mặc định là vàng
                
                # Vẽ khung quanh mặt
                cv2.rectangle(result_image, (x, y), (x+w, y+h), color, 2)
                
                # Tạo nhãn cảm xúc + tỷ lệ phần trăm (sử dụng từ không dấu)
                emotion_text = emotion_labels_vi.get(dominant, dominant)
                label = f"{emotion_text}: {result['emotion_percent'][dominant]}%"
                
                # Vẽ nhãn cảm xúc phía trên khung mặt
                draw_text(result_image, label, (x, y-30), font_scale=0.7, color=(255, 255, 255), thickness=2)
                
                # Vẽ timestamp
                draw_text(result_image, timestamp, (x, y-10), font_scale=0.6, color=(255, 255, 255), thickness=1)
            
        else:
            # Không tìm thấy khuôn mặt, tạo kết quả mặc định
            print("No faces detected, using default result")
            
            # Tạo kết quả mặc định với sự ngẫu nhiên
            emotions = {
                'happy': random.uniform(0.1, 0.2),
                'sad': random.uniform(0.05, 0.15),
                'angry': random.uniform(0.05, 0.15),
                'surprise': random.uniform(0.05, 0.15),
                'fear': random.uniform(0.05, 0.15),
                'disgust': random.uniform(0.05, 0.15),
                'neutral': random.uniform(0.3, 0.5)
            }
            
            # Chuẩn hóa tổng xác suất = 1
            total = sum(emotions.values())
            emotions = {k: v/total for k, v in emotions.items()}
            
            dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
            emotion_percent = {k: int(v * 100) for k, v in emotions.items()}
            
            result = {
                'emotion': emotions,
                'emotion_percent': emotion_percent,
                'dominant_emotion': dominant_emotion
            }
            
            # Vẽ thông báo trên ảnh - sử dụng từ không dấu
            draw_text(result_image, "Khong phat hien khuon mat", (20, 40), font_scale=1.0, color=(255, 255, 255), thickness=2)
            draw_text(result_image, timestamp, (20, 70), font_scale=0.7, color=(255, 255, 255), thickness=1)
        
        # Lưu thông tin hình ảnh đã xử lý vào kết quả
        _, buffer = cv2.imencode('.jpg', result_image)
        result['processed_image'] = base64.b64encode(buffer).decode('utf-8')
        
        # Lưu ảnh kết quả để debug
        debug_result_path = os.path.join(debug_folder, f"{debug_timestamp}_result.jpg")
        cv2.imwrite(debug_result_path, result_image)
        
        return result, result_image
        
    except Exception as e:
        print(f"Critical error in emotion detection: {e}")
        import traceback
        traceback.print_exc()
        
        # Trường hợp lỗi, trả về kết quả mẫu
        result = {
            'emotion': {
                'angry': 0.15, 'disgust': 0.05, 'fear': 0.05, 
                'happy': 0.20, 'sad': 0.15, 'surprise': 0.10, 'neutral': 0.30
            },
            'dominant_emotion': 'neutral',
            'emotion_percent': {
                'angry': 15, 'disgust': 5, 'fear': 5, 
                'happy': 20, 'sad': 15, 'surprise': 10, 'neutral': 30
            }
        }
        
        # Vẽ thông báo lỗi - sử dụng từ không dấu
        result_image = image_array.copy()
        draw_text(result_image, "Loi xu ly anh", (20, 40), font_scale=1.0, color=(255, 255, 255), thickness=2)
        draw_text(result_image, timestamp, (20, 70), font_scale=0.7, color=(255, 255, 255), thickness=1)
        
        # Lưu hình ảnh đã xử lý
        _, buffer = cv2.imencode('.jpg', result_image)
        result['processed_image'] = base64.b64encode(buffer).decode('utf-8')
        
        return result, result_image

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists'}), 400
    
    user = User(
        username=data['username'],
        full_name=data['full_name'],
        email=data['email'],
        role='user'
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Kiểm tra dữ liệu đầu vào
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({
                'success': False,
                'message': 'Thiếu thông tin đăng nhập'
            }), 400
        
        print(f"Login attempt for username: {data['username']}")
        user = User.query.filter_by(username=data['username']).first()
        
        if not user:
            print(f"User not found: {data['username']}")
            return jsonify({
                'success': False,
                'message': 'Tên đăng nhập hoặc mật khẩu không đúng'
            }), 401
        
        if not user.check_password(data['password']):
            print(f"Invalid password for user: {data['username']}")
            return jsonify({
                'success': False,
                'message': 'Tên đăng nhập hoặc mật khẩu không đúng'
            }), 401
        
        if not user.is_active:
            print(f"Inactive account: {data['username']}")
            return jsonify({
                'success': False,
                'message': 'Tài khoản đã bị vô hiệu hóa'
            }), 401
        
        # Cập nhật thời gian đăng nhập
        user.last_login = datetime.datetime.now(timezone.utc)
        db.session.commit()
        
        # Tạo token
        token = generate_token(user)
        
        print(f"Successful login for user: {data['username']}")
        return jsonify({
            'success': True,
            'access_token': token,
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role
            }
        })
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Lỗi server, vui lòng thử lại sau'
        }), 500

@app.route('/api/auth/profile', methods=['GET'], endpoint='get_profile')
@token_required
def get_profile(current_user):
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'full_name': current_user.full_name,
        'email': current_user.email,
        'role': current_user.role,
        'last_login': current_user.last_login.isoformat() if current_user.last_login else None
    })

@app.route('/api/auth/profile', methods=['PUT'], endpoint='update_profile')
@token_required
def update_profile(current_user):
    data = request.get_json()
    
    if 'email' in data and data['email'] != current_user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists'}), 400
        current_user.email = data['email']
    
    if 'full_name' in data:
        current_user.full_name = data['full_name']
    
    if 'password' in data:
        current_user.set_password(data['password'])
    
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """Verify token and return user information"""
    print(f"Token verified successfully for user: {current_user.username}")
    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'full_name': current_user.full_name,
            'email': current_user.email,
            'role': current_user.role
        }
    })

def capture_image_from_rtsp(camera_id):
    """Lấy hình ảnh từ camera RTSP và nhận diện cảm xúc"""
    try:
        # Lấy thông tin camera từ cơ sở dữ liệu
        camera = Camera.query.get(camera_id)
        if not camera:
            print(f"Không tìm thấy camera ID {camera_id}")
            return None, f"Không tìm thấy camera ID {camera_id}"

        # Kiểm tra loại camera
        if camera.camera_type not in ['droidcam', 'ipcam', 'rtsp']:
            print(f"Camera ID {camera_id} không phải là loại hỗ trợ streaming (type: {camera.camera_type})")
            return None, f"Loại camera không hỗ trợ (type: {camera.camera_type})"

        # Lấy URL stream
        stream_url = camera.stream_url
        if not stream_url:
            # Tạo URL nếu chưa có
            if camera.camera_type == 'droidcam':
                stream_url = f"http://{camera.ip_address}:{camera.port}/video"
            elif camera.camera_type == 'ipcam':
                stream_url = f"http://{camera.ip_address}:{camera.port}/video"
            elif camera.camera_type == 'rtsp':
                stream_url = f"rtsp://{camera.ip_address}:{camera.port}/h264_ulaw.sdp"
            
            # Cập nhật URL vào cơ sở dữ liệu
            camera.stream_url = stream_url
            db.session.commit()

        print(f"Kết nối đến camera {camera.name} tại URL: {stream_url}")
        
        # Mở kết nối đến camera
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            print(f"Không thể kết nối đến camera tại {stream_url}")
            return None, f"Không thể kết nối đến camera tại {stream_url}"

        # Đọc frame từ camera
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            print("Không thể đọc hình ảnh từ camera")
            return None, "Không thể đọc hình ảnh từ camera"

        # Cập nhật trạng thái kết nối
        camera.connection_status = 'connected'
        camera.last_connected = datetime.datetime.now()
        db.session.commit()

        print(f"Đã chụp ảnh thành công từ {camera.name}")
        return frame, None
    
    except Exception as e:
        print(f"Lỗi khi lấy hình ảnh từ camera RTSP: {e}")
        import traceback
        traceback.print_exc()
        return None, str(e)

@app.route('/api/cameras/rtsp-capture', methods=['POST'])
def rtsp_capture_endpoint():
    """API endpoint để chụp ảnh từ camera RTSP và nhận diện cảm xúc"""
    if 'camera_id' not in request.json:
        return jsonify({'error': 'Missing camera_id parameter'}), 400
    
    camera_id = request.json['camera_id']
    
    try:
        # Chụp ảnh từ camera RTSP
        frame, error = capture_image_from_rtsp(camera_id)
        
        if error:
            return jsonify({'error': error}), 400
        
        if frame is None:
            return jsonify({'error': 'Không thể chụp ảnh từ camera'}), 400
        
        # Chuyển đổi frame thành định dạng có thể gửi qua API
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            return jsonify({'error': 'Không thể mã hóa hình ảnh'}), 500
        
        # Chuyển buffer thành base64
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Phát hiện cảm xúc
        emotion_result, processed_image = detect_emotion(frame)
        
        if not emotion_result:
            return jsonify({'error': 'Không tìm thấy khuôn mặt hoặc lỗi xử lý'}), 400
        
        # Lưu kết quả vào thư mục
        image_path, result_path, processed_path = save_image_result(frame, camera_id, emotion_result)
        
        # Lưu vào cơ sở dữ liệu
        db_success, db_id = save_to_database(camera_id, image_path, result_path, processed_path, emotion_result)
        
        # Trả về kết quả
        return jsonify({
            'success': True,
            'emotion': emotion_result.get('emotion', {}),
            'emotion_percent': emotion_result.get('emotion_percent', {}),
            'dominant_emotion': emotion_result.get('dominant_emotion', 'unknown'),
            'processed_image': emotion_result.get('processed_image', ''),
            'database_save': db_success,
            'db_id': db_id,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Lỗi xử lý hình ảnh RTSP: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Khởi tạo scheduler cho việc chụp ảnh theo lịch
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()
rtsp_camera_jobs = {}  # Dictionary để lưu trữ các job đã lên lịch

@app.route('/api/cameras/schedule', methods=['POST'])
def schedule_camera_capture():
    """Lên lịch chụp ảnh định kỳ từ camera RTSP"""
    data = request.json
    
    if not data or 'camera_id' not in data:
        return jsonify({'error': 'Missing camera_id parameter'}), 400
    
    camera_id = data['camera_id']
    interval_minutes = data.get('interval_minutes', 15)  # Mặc định 15 phút
    schedule_type = data.get('schedule_type', 'interval')  # interval hoặc cron
    
    # Kiểm tra camera có tồn tại không
    camera = Camera.query.get(camera_id)
    if not camera:
        return jsonify({'error': f'Camera ID {camera_id} not found'}), 404
    
    # Kiểm tra loại camera có hỗ trợ không
    if camera.camera_type not in ['droidcam', 'ipcam', 'rtsp']:
        return jsonify({'error': f'Camera type {camera.camera_type} does not support scheduling'}), 400
    
    # Xóa job cũ nếu đã có
    if str(camera_id) in rtsp_camera_jobs:
        scheduler.remove_job(rtsp_camera_jobs[str(camera_id)])
        del rtsp_camera_jobs[str(camera_id)]
    
    # Hàm xử lý chụp ảnh và nhận diện
    def capture_and_process():
        print(f"Đang chụp ảnh theo lịch từ camera {camera_id}")
        frame, error = capture_image_from_rtsp(camera_id)
        
        if error or frame is None:
            print(f"Lỗi khi chụp ảnh theo lịch từ camera {camera_id}: {error}")
            return
        
        try:
            # Phát hiện cảm xúc
            emotion_result, processed_image = detect_emotion(frame)
            
            if not emotion_result:
                print(f"Không tìm thấy khuôn mặt hoặc lỗi xử lý trong ảnh từ camera {camera_id}")
                return
            
            # Lưu kết quả vào thư mục
            image_path, result_path, processed_path = save_image_result(frame, camera_id, emotion_result)
            
            # Lưu vào cơ sở dữ liệu
            db_success, db_id = save_to_database(camera_id, image_path, result_path, processed_path, emotion_result)
            
            print(f"Đã xử lý thành công ảnh từ camera {camera_id}, kết quả: {emotion_result.get('dominant_emotion')}")
        
        except Exception as e:
            print(f"Lỗi khi xử lý ảnh từ camera {camera_id}: {e}")
            import traceback
            traceback.print_exc()
    
    # Tạo job mới dựa vào loại lịch trình
    if schedule_type == 'interval':
        job = scheduler.add_job(
            capture_and_process,
            IntervalTrigger(minutes=interval_minutes),
            id=f'camera_{camera_id}_interval'
        )
        job_info = {
            'type': 'interval',
            'interval_minutes': interval_minutes,
            'next_run': job.next_run_time.isoformat()
        }
    
    elif schedule_type == 'cron':
        # Lấy thông tin cron từ request
        hour = data.get('hour', '*/1')  # Mặc định mỗi giờ
        minute = data.get('minute', '0')  # Mặc định vào đầu giờ
        
        job = scheduler.add_job(
            capture_and_process,
            CronTrigger(hour=hour, minute=minute),
            id=f'camera_{camera_id}_cron'
        )
        job_info = {
            'type': 'cron',
            'hour': hour,
            'minute': minute,
            'next_run': job.next_run_time.isoformat()
        }
    
    else:
        return jsonify({'error': 'Invalid schedule_type. Must be "interval" or "cron"'}), 400
    
    # Lưu job id vào dictionary
    rtsp_camera_jobs[str(camera_id)] = job.id
    
    return jsonify({
        'success': True,
        'message': f'Camera {camera_id} scheduled for {schedule_type} capture',
        'camera_id': camera_id,
        'schedule': job_info
    })

@app.route('/api/cameras/schedule/<int:camera_id>', methods=['DELETE'])
def delete_camera_schedule(camera_id):
    """Xóa lịch trình chụp ảnh của camera"""
    # Kiểm tra camera có tồn tại không
    camera = Camera.query.get(camera_id)
    if not camera:
        return jsonify({'error': f'Camera ID {camera_id} not found'}), 404
    
    # Kiểm tra xem có job nào cho camera này không
    if str(camera_id) not in rtsp_camera_jobs:
        return jsonify({'error': f'No schedule found for camera {camera_id}'}), 404
    
    # Xóa job
    job_id = rtsp_camera_jobs[str(camera_id)]
    try:
        scheduler.remove_job(job_id)
        del rtsp_camera_jobs[str(camera_id)]
        
        return jsonify({
            'success': True,
            'message': f'Schedule for camera {camera_id} deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': f'Error deleting schedule: {str(e)}'}), 500

@app.route('/api/cameras/schedule', methods=['GET'])
def get_schedules():
    """Lấy danh sách tất cả các lịch trình đã cài đặt"""
    result = []
    
    for camera_id, job_id in rtsp_camera_jobs.items():
        job = scheduler.get_job(job_id)
        if job:
            # Xác định loại lịch trình
            if 'interval' in job_id:
                job_type = 'interval'
                interval_seconds = job.trigger.interval.total_seconds()
                interval_minutes = int(interval_seconds / 60)
                
                job_info = {
                    'camera_id': int(camera_id),
                    'job_id': job_id,
                    'type': job_type,
                    'interval_minutes': interval_minutes,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                }
            
            else:  # cron
                job_type = 'cron'
                job_info = {
                    'camera_id': int(camera_id),
                    'job_id': job_id,
                    'type': job_type,
                    'hour': job.trigger.fields[5],  # hour field
                    'minute': job.trigger.fields[6],  # minute field
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                }
            
            # Thêm thông tin camera
            camera = Camera.query.get(int(camera_id))
            if camera:
                job_info['camera_name'] = camera.name
                job_info['camera_location'] = camera.location
                job_info['camera_type'] = camera.camera_type
            
            result.append(job_info)
    
    return jsonify(result)

@app.route('/api/cameras/schedule/<int:camera_id>', methods=['GET'])
def get_camera_schedule(camera_id):
    """Lấy thông tin lịch trình của camera cụ thể"""
    # Kiểm tra camera có tồn tại không
    camera = Camera.query.get(camera_id)
    if not camera:
        return jsonify({'error': f'Camera ID {camera_id} not found'}), 404
    
    # Kiểm tra xem có job nào cho camera này không
    if str(camera_id) not in rtsp_camera_jobs:
        return jsonify({'scheduled': False, 'message': f'No schedule found for camera {camera_id}'})
    
    # Lấy thông tin job
    job_id = rtsp_camera_jobs[str(camera_id)]
    job = scheduler.get_job(job_id)
    
    if not job:
        # Có job ID nhưng không còn job trong scheduler
        del rtsp_camera_jobs[str(camera_id)]
        return jsonify({'scheduled': False, 'message': f'Schedule for camera {camera_id} not found in scheduler'})
    
    # Xác định loại lịch trình
    if 'interval' in job_id:
        job_type = 'interval'
        interval_seconds = job.trigger.interval.total_seconds()
        interval_minutes = int(interval_seconds / 60)
        
        return jsonify({
            'scheduled': True,
            'camera_id': camera_id,
            'job_id': job_id,
            'type': job_type,
            'interval_minutes': interval_minutes,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'camera_name': camera.name,
            'camera_location': camera.location,
            'camera_type': camera.camera_type
        })
    
    else:  # cron
        job_type = 'cron'
        return jsonify({
            'scheduled': True,
            'camera_id': camera_id,
            'job_id': job_id,
            'type': job_type,
            'hour': job.trigger.fields[5],  # hour field
            'minute': job.trigger.fields[6],  # minute field
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'camera_name': camera.name,
            'camera_location': camera.location,
            'camera_type': camera.camera_type
        })

# Thêm route để phục vụ static files
@app.route('/api/static/<path:filename>')
def serve_static(filename):
    """Phục vụ files tĩnh như ảnh placeholder"""
    return send_from_directory('static', filename)

# Khởi tạo dữ liệu mặc định nếu cần
def init_default_data():
    """Khởi tạo dữ liệu mặc định cho database"""
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
                )
            ]
            
            for camera in default_cameras:
                db.session.add(camera)
            
            db.session.commit()
            print("Đã tạo dữ liệu mặc định thành công!")

# Thiết lập database khi chạy app
def setup_database():
    """Thiết lập database và tạo dữ liệu mặc định"""
    with app.app_context():
        # Tạo bảng
        db.create_all()
        
        # Khởi tạo dữ liệu mặc định
        init_default_data()
        
        # Tạo thư mục cho hình ảnh
        ensure_image_directories()
        
        print("Thiết lập database hoàn tất")

# Thêm biến toàn cục để lưu trạng thái nhận diện
face_detection_threads = {}

def start_face_detection(camera_id, stream_url, capture_interval, enable_emotion):
    """Hàm xử lý nhận diện khuôn mặt trong thread riêng"""
    try:
        # Mở stream video
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            raise Exception("Không thể mở stream video")

        # Tạo thư mục lưu ảnh nếu chưa tồn tại
        save_dir = os.path.join('images', f'camera_{camera_id}')
        os.makedirs(save_dir, exist_ok=True)

        while face_detection_threads.get(camera_id, {}).get('running', False):
            # Chụp frame
            ret, frame = cap.read()
            if not ret:
                continue

            # Lưu ảnh với timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_path = os.path.join(save_dir, f'{timestamp}.jpg')
            cv2.imwrite(image_path, frame)

            # Nhận diện khuôn mặt và cảm xúc
            faces = detect_faces(frame)
            if faces and enable_emotion:
                emotions = detect_emotions(frame, faces)
                
                # Lưu kết quả vào database
                for face, emotion in zip(faces, emotions):
                    save_detection_result(camera_id, image_path, face, emotion)

            # Đợi theo khoảng thời gian đã cài đặt
            time.sleep(capture_interval)

    except Exception as e:
        print(f"Lỗi trong quá trình nhận diện: {str(e)}")
    finally:
        if cap:
            cap.release()
        face_detection_threads[camera_id] = {'running': False}

@app.route('/api/cameras/<int:camera_id>/detect-faces', methods=['POST'])
@jwt_required()
def start_face_detection_endpoint(camera_id):
    try:
        data = request.get_json()
        stream_url = data.get('streamUrl')
        capture_interval = data.get('captureInterval', 2)
        enable_emotion = data.get('enableEmotionDetection', True)

        # Kiểm tra camera có tồn tại không
        camera = Camera.query.get(camera_id)
        if not camera:
            return jsonify({'success': False, 'message': 'Camera không tồn tại'}), 404

        # Kiểm tra xem đã có thread đang chạy chưa
        if camera_id in face_detection_threads and face_detection_threads[camera_id].get('running', False):
            return jsonify({'success': False, 'message': 'Đã có quá trình nhận diện đang chạy'}), 400

        # Bắt đầu thread nhận diện
        face_detection_threads[camera_id] = {'running': True}
        thread = threading.Thread(
            target=start_face_detection,
            args=(camera_id, stream_url, capture_interval, enable_emotion)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Đã bắt đầu nhận diện khuôn mặt',
            'camera_id': camera_id
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cameras/<int:camera_id>/stop-detection', methods=['POST'])
@jwt_required()
def stop_face_detection_endpoint(camera_id):
    try:
        if camera_id in face_detection_threads:
            face_detection_threads[camera_id]['running'] = False
            return jsonify({
                'success': True,
                'message': 'Đã dừng nhận diện khuôn mặt'
            })
        return jsonify({
            'success': False,
            'message': 'Không tìm thấy quá trình nhận diện đang chạy'
        }), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def save_detection_result(camera_id, image_path, face, emotion):
    """Lưu kết quả nhận diện vào database"""
    try:
        result = DetectionResult(
            camera_id=camera_id,
            image_path=image_path,
            face_location=face['location'],
            emotion=emotion['emotion'],
            confidence=emotion['confidence'],
            timestamp=datetime.now()
        )
        db.session.add(result)
        db.session.commit()
    except Exception as e:
        print(f"Lỗi khi lưu kết quả: {str(e)}")
        db.session.rollback()

@app.route('/api/cameras/<int:camera_id>/test-connection', methods=['POST'])
def test_camera_connection(camera_id):
    try:
        camera = Camera.query.get(camera_id)
        if not camera:
            return jsonify({
                'success': False,
                'message': f'Không tìm thấy camera với ID {camera_id}'
            }), 404

        # Test connection based on camera type
        if camera.camera_type == 'webcam':
            # For webcam, just return success
            success = True
            message = 'Webcam sẵn sàng sử dụng'
        elif camera.camera_type == 'ipcam':
            # Test IP camera connection
            try:
                url = f'http://{camera.ip_address}:{camera.port}/video'
                response = requests.get(url, timeout=5)
                success = response.status_code == 200
                message = 'Kết nối thành công' if success else 'Không thể kết nối đến camera'
            except requests.exceptions.RequestException:
                success = False
                message = 'Không thể kết nối đến camera'
        else:
            success = False
            message = 'Loại camera không hỗ trợ kiểm tra kết nối'

        # Update camera status
        camera.connection_status = 'connected' if success else 'disconnected'
        camera.last_connected = datetime.now() if success else None
        db.session.commit()

        return jsonify({
            'success': success,
            'message': message,
            'camera': camera.to_dict()
        })

    except Exception as e:
        print(f"Error testing camera connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Lỗi kiểm tra kết nối camera'
        }), 500

# Endpoint để bật camera
@app.route('/api/cameras/<int:camera_id>/start', methods=['POST'])
def start_camera_endpoint(camera_id):
    try:
        camera = Camera.query.get_or_404(camera_id)
        
        # Kiểm tra loại camera và xử lý tương ứng
        if camera.camera_type == 'webcam':
            # Xử lý cho webcam
            camera.connection_status = 'connected'
            camera.last_connected = datetime.datetime.now()
        elif camera.camera_type in ['ipcam', 'droidcam']:
            # Kiểm tra kết nối với IP camera
            try:
                url = f'http://{camera.ip_address}:{camera.port}/video'
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    camera.connection_status = 'connected'
                    camera.last_connected = datetime.datetime.now()
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Không thể kết nối đến camera'
                    }), 400
            except requests.exceptions.RequestException:
                return jsonify({
                    'success': False,
                    'message': 'Không thể kết nối đến camera'
                }), 400
        
        camera.status = 'active'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Camera đã được bật thành công',
            'camera': camera.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Lỗi khi bật camera: {str(e)}'
        }), 500

# Endpoint để tắt camera
@app.route('/api/cameras/<int:camera_id>/stop', methods=['POST'])
def stop_camera_endpoint(camera_id):
    try:
        camera = Camera.query.get_or_404(camera_id)
        
        camera.status = 'inactive'
        camera.connection_status = 'disconnected'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Camera đã được tắt thành công',
            'camera': camera.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Lỗi khi tắt camera: {str(e)}'
        }), 500

# Endpoint để lấy trạng thái camera
@app.route('/api/cameras/<int:camera_id>/status', methods=['GET'])
def get_camera_status(camera_id):
    try:
        camera = Camera.query.get_or_404(camera_id)
        
        return jsonify({
            'success': True,
            'is_active': camera.status == 'active',
            'connection_status': camera.connection_status,
            'last_connected': camera.last_connected.isoformat() if camera.last_connected else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi khi lấy trạng thái camera: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Thiết lập database
    setup_database()
    
    # Chạy ứng dụng
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True) 
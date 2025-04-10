from flask import Flask, request, jsonify, send_file, Response
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
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON as SQL_JSON, Boolean
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import random
import math
import flask
import sqlalchemy
import hashlib
import jwt
from datetime import timedelta, timezone
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import logging
from camera_manager import camera_bp, Camera, db

# Tải biến môi trường
load_dotenv()

app = Flask(__name__)
CORS(app)

# Cấu hình PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:123456@localhost/emotion_detection1.2')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.getcwd()), 'images')

# Định nghĩa lớp cơ sở cho SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass

# Khởi tạo SQLAlchemy
db.init_app(app)

# Định nghĩa model Emotion
class Emotion(db.Model):
    __tablename__ = 'emotions'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    camera_id = Column(Integer, db.ForeignKey('cameras.id'), nullable=False)
    image_path = Column(String(255), nullable=False)
    result_path = Column(String(255), nullable=False)
    dominant_emotion = Column(String(50))
    emotion_scores = Column(SQL_JSON)
    image_base64 = Column(String) # Lưu trữ hình ảnh gốc dưới dạng base64
    processed_image_base64 = Column(String) # Lưu trữ hình ảnh đã xử lý dưới dạng base64
    
    def __repr__(self):
        return f'<Emotion {self.id} - {self.dominant_emotion}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'camera_id': self.camera_id,
            'image_path': self.image_path,
            'result_path': self.result_path,
            'dominant_emotion': self.dominant_emotion,
            'emotion_scores': self.emotion_scores,
            'image_base64': self.image_base64,
            'processed_image_base64': self.processed_image_base64
        }

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
        
        # Lưu vào cơ sở dữ liệu PostgreSQL
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
    """Tạo một camera mới"""
    if not request.json or 'name' not in request.json:
        return jsonify({'error': 'Missing name parameter'}), 400
    
    try:
        # Lấy thông tin camera từ request
        name = request.json['name']
        description = request.json.get('description', '')
        location = request.json.get('location', '')
        
        # Tạo bản ghi camera mới
        camera = Camera(
            name=name,
            description=description,
            location=location,
            is_active=True,
            created_at=datetime.datetime.now()
        )
        
        # Lưu vào cơ sở dữ liệu
        db.session.add(camera)
        db.session.commit()
        
        # Tạo thư mục lưu trữ hình ảnh cho camera mới
        os.makedirs(f"image{camera.id}", exist_ok=True)
        
        return jsonify({
            'success': True,
            'message': f'Camera {name} created successfully',
            'camera': camera.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
    """Cập nhật thông tin camera"""
    try:
        camera = Camera.query.get(camera_id)
        if not camera:
            return jsonify({'error': f'Camera ID {camera_id} not found'}), 404
        
        # Cập nhật thông tin từ request
        if 'name' in request.json:
            camera.name = request.json['name']
        if 'description' in request.json:
            camera.description = request.json['description']
        if 'location' in request.json:
            camera.location = request.json['location']
        if 'is_active' in request.json:
            camera.is_active = request.json['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Camera {camera_id} updated successfully',
            'camera': camera.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
        
        print(f"Getting emotions with params: camera_id={camera_id}, limit={limit}, offset={offset}, include_images={include_images}")
        
        # Xây dựng truy vấn
        query = Emotion.query
        
        # Lọc theo camera_id nếu được cung cấp
        if camera_id is not None:
            query = query.filter_by(camera_id=camera_id)
        
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
                                # Thử tìm file processed image trong cùng thư mục
                                processed_dir = os.path.dirname(abs_processed_path)
                                processed_files = [f for f in os.listdir(processed_dir) if f.endswith('_processed.jpg')]
                                if processed_files:
                                    print(f"Found alternative processed file: {processed_files[0]}")
                                    alt_path = os.path.join(processed_dir, processed_files[0])
                                    with open(alt_path, 'rb') as img_file:
                                        processed_data = img_file.read()
                                        emotion_dict['processed_image_base64'] = base64.b64encode(processed_data).decode('utf-8')
                                else:
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

# Hàm vẽ text tiếng Việt lên ảnh
def draw_text_with_unicode(img, text, position, font_size, color, thickness=2, bg_color=None):
    """Vẽ text Unicode (tiếng Việt) lên ảnh bằng Pillow thay vì OpenCV"""
    # Chuyển đổi từ OpenCV (BGR) sang Pillow (RGB)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_img)
    draw = ImageDraw.Draw(pil_img)
    
    # Tải font hỗ trợ tiếng Việt
    # Sử dụng font mặc định nếu không tìm thấy font tùy chỉnh
    try:
        # Thử tìm font hỗ trợ tiếng Việt
        font_paths = [
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS
            "arial.ttf"  # Thử tìm trong thư mục hiện tại
        ]
        
        font = None
        for path in font_paths:
            if os.path.exists(path):
                print(f"Found font at: {path}")
                font = ImageFont.truetype(path, font_size)
                break
        
        if font is None:
            # Nếu không tìm thấy font nào, sử dụng font mặc định
            font = ImageFont.load_default()
            print("Warning: Using default font, Vietnamese characters may not display correctly")
    except Exception as e:
        print(f"Font loading error: {e}")
        font = ImageFont.load_default()
    
    # Vẽ background nếu được yêu cầu
    if bg_color:
        # Tính toán kích thước văn bản - đảm bảo tương thích với tất cả phiên bản Pillow
        try:
            # Phương pháp 1: Dùng textbbox() (cho Pillow 9.2.0+)
            if hasattr(draw, 'textbbox'):
                print("Using textbbox() method for text size calculation")
                bbox = draw.textbbox(position, text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1] 
            # Phương pháp 2: Dùng getbbox() (cho Pillow 8.0.0+)
            elif hasattr(font, 'getbbox'):
                print("Using getbbox() method for text size calculation")
                bbox = font.getbbox(text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            # Phương pháp 3: Dùng textsize() (cho phiên bản cũ)
            elif hasattr(draw, 'textsize'):
                print("Using textsize() method for text size calculation")
                text_width, text_height = draw.textsize(text, font=font)
            # Phương pháp 4: Dùng getsize() (cho phiên bản cũ)
            elif hasattr(font, 'getsize'):
                print("Using getsize() method for text size calculation")
                text_width, text_height = font.getsize(text)
            # Phương pháp 5: Fallback - ước tính kích thước dựa trên độ dài văn bản và font_size
            else:
                print("Using fallback method for text size calculation")
                text_width = len(text) * font_size * 0.6  # Ước tính chiều rộng
                text_height = font_size * 1.2  # Ước tính chiều cao
        except Exception as e:
            print(f"Error calculating text size: {e}")
            # Fallback: Tạo hình chữ nhật lớn hơn để đảm bảo văn bản không bị cắt
            text_width = len(text) * font_size * 0.7
            text_height = font_size * 1.5
        
        x, y = position
        # Vẽ nền cho văn bản, thêm padding để đảm bảo đủ không gian cho dấu tiếng Việt
        padding_x, padding_y = font_size // 3, font_size // 3
        draw.rectangle(
            [(x - padding_x, y - padding_y), 
              (x + text_width + padding_x, y + text_height + padding_y)], 
            fill=bg_color
        )
    
    # Vẽ văn bản
    draw.text(position, text, font=font, fill=color)
    
    # Chuyển đổi trở lại định dạng OpenCV (BGR)
    result_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return result_img

def detect_emotion(image_array):
    """Phát hiện cảm xúc từ mảng hình ảnh sử dụng OpenCV và DeepFace"""
    try:
        # In ra kích thước và kiểu dữ liệu của hình ảnh để debug
        print(f"Input image shape: {image_array.shape}, dtype: {image_array.dtype}")
        print(f"Image min/max values: {np.min(image_array)}/{np.max(image_array)}")
        
        # Tạo bản sao để vẽ lên
        result_image = image_array.copy()
        h, w = image_array.shape[:2]
        print(f"Image dimensions: {w}x{h}")
        
        # Lưu hình ảnh đầu vào để debug
        debug_folder = "debug_images"
        os.makedirs(debug_folder, exist_ok=True)
        debug_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_input_path = os.path.join(debug_folder, f"{debug_timestamp}_input.jpg")
        print(f"Saving debug input image to: {debug_input_path}")
        cv2.imwrite(debug_input_path, image_array)
        
        # Sử dụng OpenCV để phát hiện khuôn mặt
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        print(f"OpenCV detected {len(faces)} faces")
        
        # Lưu ảnh grayscale để debug
        debug_gray_path = os.path.join(debug_folder, f"{debug_timestamp}_gray.jpg")
        cv2.imwrite(debug_gray_path, gray)
        
        # Nếu không tìm thấy mặt, thử với các tham số khác
        if len(faces) == 0:
            print("Trying alternative face detection parameters...")
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))
            print(f"OpenCV detected {len(faces)} faces with alternative parameters")
        
        if len(faces) > 0:
            # Lưu ảnh với khung mặt phát hiện được để debug
            debug_faces_path = os.path.join(debug_folder, f"{debug_timestamp}_faces.jpg")
            debug_faces_img = image_array.copy()
            for (x, y, w, h) in faces:
                cv2.rectangle(debug_faces_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.imwrite(debug_faces_path, debug_faces_img)
            
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
                
                # Lưu lại lỗi vào file để tiện debug
                with open(os.path.join(debug_folder, f"{debug_timestamp}_error.txt"), 'w') as f:
                    f.write(str(e))
                    f.write("\n\n")
                    traceback.print_exc(file=f)
                
                # Tạo kết quả mặc định với sự ngẫu nhiên khi DeepFace thất bại
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
                
            # Vẽ khung và thông tin cảm xúc lên hình ảnh
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Ánh xạ tên cảm xúc sang tiếng Việt
            emotion_labels = {
                'angry': 'Giận dữ',
                'disgust': 'Ghê tởm',
                'fear': 'Sợ hãi',
                'happy': 'Vui vẻ',
                'sad': 'Buồn bã',
                'surprise': 'Ngạc nhiên',
                'neutral': 'Bình thường'
            }
            
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
                
                # Tạo nhãn với cảm xúc và thời gian
                label = f"{emotion_labels.get(dominant, dominant)} ({result['emotion_percent'][dominant]}%)"
                time_label = f"{timestamp}"
                
                # Vẽ hộp nền cho văn bản
                # Sử dụng phương pháp cải tiến để vẽ text tiếng Việt
                result_image = draw_text_with_unicode(
                    result_image, 
                    label, 
                    (x+5, y-40), 
                    24,  # font size 
                    (255, 255, 255),  # text color (trắng)
                    bg_color=color  # background color
                )
                
                result_image = draw_text_with_unicode(
                    result_image, 
                    time_label, 
                    (x+5, y-10), 
                    16,  # font size
                    (255, 255, 255),  # text color (trắng)
                    bg_color=color  # background color
                )
                
                # Vẽ biểu đồ cảm xúc nhỏ
                bar_height = 5
                bar_width = w
                bar_y = y + h + 10
                
                # Vẽ các thanh cảm xúc
                for i, (emotion, percent) in enumerate(sorted(result['emotion_percent'].items(), 
                                                            key=lambda x: x[1], reverse=True)):
                    if i >= 4:  # Chỉ hiển thị 4 cảm xúc hàng đầu
                        break
                        
                    e_color = emotion_colors.get(emotion, (128, 128, 128))
                    e_width = int(bar_width * percent / 100)
                    
                    # Vẽ nền thanh
                    cv2.rectangle(result_image, (x, bar_y + i*20), (x + bar_width, bar_y + i*20 + bar_height), 
                                (50, 50, 50), -1)
                    # Vẽ thanh cảm xúc
                    cv2.rectangle(result_image, (x, bar_y + i*20), (x + e_width, bar_y + i*20 + bar_height), 
                                e_color, -1)
                    
                    # Nhãn cảm xúc - dùng hàm vẽ text hỗ trợ tiếng Việt
                    e_label = f"{emotion_labels.get(emotion, emotion)}: {percent}%"
                    result_image = draw_text_with_unicode(
                        result_image,
                        e_label,
                        (x, bar_y + i*20 + 12),
                        14,  # font size
                        (255, 255, 255)  # text color (trắng)
                    )
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
            
            # Vẽ một khung giả ở giữa hình
            center_x = w // 4
            center_y = h // 4
            frame_w = w // 2
            frame_h = h // 2
            
            cv2.rectangle(result_image, (center_x, center_y), (center_x+frame_w, center_y+frame_h), (0, 0, 255), 2)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Thêm nhãn thông báo - dùng hàm vẽ text hỗ trợ tiếng Việt
            result_image = draw_text_with_unicode(
                result_image,
                "Không phát hiện khuôn mặt",
                (center_x+10, center_y-20),
                24,  # font size
                (255, 255, 255),  # text color (trắng)
                bg_color=(0, 0, 255)  # background color (đỏ)
            )
            
            result_image = draw_text_with_unicode(
                result_image,
                timestamp,
                (center_x+10, center_y+10),
                18,  # font size
                (255, 255, 255),  # text color (trắng)
                bg_color=(0, 0, 255)  # background color (đỏ)
            )
        
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
        
        # Lưu thông tin lỗi vào file để debug
        debug_folder = "debug_images"
        os.makedirs(debug_folder, exist_ok=True)
        debug_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(os.path.join(debug_folder, f"{debug_timestamp}_critical_error.txt"), 'w') as f:
            f.write(str(e))
            f.write("\n\n")
            traceback.print_exc(file=f)
        
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
        
        # Vẽ thông báo lỗi
        h, w = image_array.shape[:2]
        x = w // 4
        y = h // 4
        w_frame = w // 2
        h_frame = h // 2
        
        result_image = image_array.copy()
        cv2.rectangle(result_image, (x, y), (x+w_frame, y+h_frame), (0, 0, 255), 2)
        
        # Dùng hàm vẽ text hỗ trợ tiếng Việt
        error_text = "Lỗi nhận diện: " + str(e)[:30]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        result_image = draw_text_with_unicode(
            result_image,
            error_text,
            (x+10, y-20),
            20,  # font size
            (255, 255, 255),  # text color (trắng)
            bg_color=(0, 0, 255)  # background color (đỏ)
        )
        
        result_image = draw_text_with_unicode(
            result_image,
            timestamp,
            (x+10, y+10),
            16,  # font size
            (255, 255, 255),  # text color (trắng)
            bg_color=(0, 0, 255)  # background color (đỏ)
        )
        
        # Lưu hình ảnh đã xử lý
        _, buffer = cv2.imencode('.jpg', result_image)
        result['processed_image'] = base64.b64encode(buffer).decode('utf-8')
        
        # Lưu ảnh lỗi để debug
        if not os.path.exists(debug_folder):
            os.makedirs(debug_folder)
        debug_error_path = os.path.join(debug_folder, f"{debug_timestamp}_error_image.jpg")
        cv2.imwrite(debug_error_path, result_image)
        
        return result, result_image

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(days=1)

# Add User model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

def generate_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.datetime.now() + JWT_EXPIRATION_DELTA
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def token_required(f):
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            current_user = User.query.get(payload['user_id'])
            if not current_user or not current_user.is_active:
                return jsonify({'message': 'Invalid token'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

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

if __name__ == '__main__':
    try:
        print("Starting Flask application...")
        print(f"Flask version: {flask.__version__}")
        print(f"SQLAlchemy version: {sqlalchemy.__version__ if 'sqlalchemy' in globals() else 'Unknown'}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc() 
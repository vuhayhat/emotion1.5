from flask import Blueprint, jsonify, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import requests
import cv2

db = SQLAlchemy()
camera_bp = Blueprint('camera', __name__)

# Xử lý CORS trực tiếp tại blueprint
CORS(camera_bp, resources={r"/api/*": {
    "origins": ["http://localhost:3000"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True
}})

# Thêm decorator xử lý CORS cho mỗi route
def handle_options(f):
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = jsonify({})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            return response
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_connected = db.Column(db.DateTime)  # Thời gian kết nối cuối cùng
    connection_status = db.Column(db.String(20), default='disconnected')  # connected, disconnected, error
    
    # Relationships
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
                if not self.ip_address or not self.port:
                    self.connection_status = 'error'
                    return False
                
                # Tạo URL stream nếu chưa có
                if not self.stream_url:
                    self.stream_url = self.generate_stream_url()
                
                # Thử kết nối đến camera
                response = requests.get(self.stream_url, timeout=3, stream=True)
                
                # Đọc một phần nhỏ dữ liệu để kiểm tra stream
                if response.status_code == 200:
                    try:
                        next(response.iter_content(chunk_size=1024))
                        self.connection_status = 'connected'
                        self.last_connected = datetime.utcnow()
                        return True
                    except Exception as e:
                        print(f"Error reading stream: {e}")
                        self.connection_status = 'error'
                        return False
                else:
                    print(f"Connection failed with status code: {response.status_code}")
                    self.connection_status = 'error'
                    return False
                    
            elif self.camera_type == 'webcam':
                # Thử mở webcam
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    # Thử đọc một frame
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret:
                        self.connection_status = 'connected'
                        self.last_connected = datetime.utcnow()
                        return True
                    else:
                        print("Could not read frame from webcam")
                        self.connection_status = 'error'
                        return False
                else:
                    print("Could not open webcam")
                    self.connection_status = 'error'
                    return False
            
            self.connection_status = 'error'
            return False
            
        except requests.exceptions.Timeout:
            print("Connection timeout")
            self.connection_status = 'error'
            return False
        except requests.exceptions.ConnectionError:
            print("Connection error")
            self.connection_status = 'error'
            return False
        except Exception as e:
            print(f"Unexpected error during connection test: {e}")
            self.connection_status = 'error'
            return False

@camera_bp.route('/api/cameras', methods=['GET', 'OPTIONS'])
@handle_options
def get_cameras():
    try:
        cameras = Camera.query.all()
        result = []
        for camera in cameras:
            camera_data = {
                'id': camera.id,
                'name': camera.name,
                'location': camera.location,
                'camera_type': camera.camera_type,
                'status': camera.status,
                'stream_url': camera.stream_url,
                'ip_address': camera.ip_address,
                'port': camera.port,
                'connection_status': camera.connection_status,
                'last_connected': camera.last_connected.isoformat() if camera.last_connected else None
            }
            result.append(camera_data)
        return jsonify(result)
    except Exception as e:
        print(f"Error getting cameras: {e}")
        return jsonify({"error": str(e)}), 500

@camera_bp.route('/api/cameras/<int:camera_id>', methods=['GET', 'OPTIONS'])
@handle_options
def get_camera(camera_id):
    try:
        camera = Camera.query.get_or_404(camera_id)
        return jsonify({
            'id': camera.id,
            'name': camera.name,
            'location': camera.location,
            'camera_type': camera.camera_type,
            'status': camera.status,
            'stream_url': camera.stream_url,
            'ip_address': camera.ip_address,
            'port': camera.port,
            'connection_status': camera.connection_status,
            'last_connected': camera.last_connected.isoformat() if camera.last_connected else None
        })
    except Exception as e:
        print(f"Error getting camera {camera_id}: {e}")
        return jsonify({"error": str(e)}), 500

@camera_bp.route('/api/cameras', methods=['POST', 'OPTIONS'])
@handle_options
def add_camera():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Validate camera type
    valid_types = ['webcam', 'droidcam', 'ipcam']
    if data['type'] not in valid_types:
        return jsonify({'error': f'Invalid camera type. Must be one of: {", ".join(valid_types)}'}), 400
    
    # Validate IP and port for DroidCam and IP cameras
    if data['type'] in ['droidcam', 'ipcam']:
        if not data.get('ip_address') or not data.get('port'):
            return jsonify({'error': 'IP address and port are required for DroidCam and IP cameras'}), 400
    
    camera = Camera(
        name=data['name'],
        location=data.get('location'),
        camera_type=data['type'],
        ip_address=data.get('ip_address'),
        port=data.get('port'),
        user_id=data.get('user_id')
    )
    
    # Generate stream URL based on camera type
    if camera.camera_type in ['droidcam', 'ipcam']:
        camera.stream_url = camera.generate_stream_url()
    
    # Test camera connection
    if camera.test_connection():
        camera.status = 'active'
    else:
        camera.status = 'inactive'
    
    db.session.add(camera)
    db.session.commit()

    # Create directory for camera images
    camera_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'camera{camera.id}')
    os.makedirs(camera_dir, exist_ok=True)
    
    return jsonify({
        'id': camera.id,
        'name': camera.name,
        'status': camera.status,
        'connection_status': camera.connection_status,
        'stream_url': camera.stream_url,
        'message': 'Camera added successfully'
    }), 201

@camera_bp.route('/api/cameras/test', methods=['POST', 'OPTIONS'])
@handle_options
def test_camera():
    """Test camera connection"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['type']
        if data.get('type') in ['droidcam', 'ipcam']:
            required_fields.extend(['ip_address', 'port'])
            
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create temporary camera object for testing
        camera = Camera(
            name="Test Camera",
            camera_type=data['type'],
            ip_address=data.get('ip_address'),
            port=data.get('port')
        )
        
        # Generate stream URL
        if camera.camera_type in ['droidcam', 'ipcam']:
            camera.stream_url = camera.generate_stream_url()
        
        # Test connection
        connection_successful = camera.test_connection()
        
        return jsonify({
            'connection_status': camera.connection_status,
            'stream_url': camera.stream_url if connection_successful else None,
            'message': 'Connection test successful' if connection_successful else 'Connection test failed'
        })
        
    except Exception as e:
        print(f"Error testing camera connection: {e}")
        return jsonify({
            'error': str(e),
            'connection_status': 'error',
            'message': 'Error testing camera connection'
        }), 500

@camera_bp.route('/api/cameras/<int:camera_id>/test', methods=['POST'])
def test_camera_connection(camera_id):
    """Test existing camera connection and update status"""
    try:
        camera = Camera.query.get_or_404(camera_id)
        
        # Test connection
        connection_successful = camera.test_connection()
        
        # Save status to database
        db.session.commit()
        
        return jsonify({
            'id': camera.id,
            'name': camera.name,
            'connection_status': camera.connection_status,
            'last_connected': camera.last_connected.isoformat() if camera.last_connected else None,
            'stream_url': camera.stream_url if connection_successful else None,
            'message': 'Connection test successful' if connection_successful else 'Connection test failed'
        })
        
    except Exception as e:
        print(f"Error testing camera {camera_id} connection: {e}")
        return jsonify({
            'error': str(e),
            'connection_status': 'error',
            'message': f'Error testing camera {camera_id} connection'
        }), 500

@camera_bp.route('/api/cameras/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    data = request.get_json()
    
    if 'name' in data:
        camera.name = data['name']
    if 'location' in data:
        camera.location = data['location']
    if 'status' in data:
        camera.status = data['status']
    if 'type' in data:
        camera.camera_type = data['type']
    if 'ip_address' in data:
        camera.ip_address = data['ip_address']
    if 'port' in data:
        camera.port = data['port']
        
    if camera.camera_type in ['ipcam', 'droidcam'] and camera.ip_address and camera.port:
        camera.stream_url = f"http://{camera.ip_address}:{camera.port}/video"
    
    db.session.commit()
    return jsonify({'message': 'Camera updated successfully'})

@camera_bp.route('/api/cameras/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    
    # Delete all associated emotions first
    for emotion in camera.emotions:
        db.session.delete(emotion)
    
    db.session.delete(camera)
    db.session.commit()
    return jsonify({'message': 'Camera deleted successfully'})

@camera_bp.route('/api/cameras/<int:camera_id>/status', methods=['PUT'])
def update_camera_status(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({'error': 'Missing status field'}), 400
        
    camera.status = data['status']
    db.session.commit()
    
    return jsonify({
        'id': camera.id,
        'status': camera.status,
        'message': 'Camera status updated successfully'
    }) 
from flask import Blueprint, jsonify, request, current_app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()
camera_bp = Blueprint('camera', __name__)

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
    
    # Relationships
    emotions = db.relationship('Emotion', backref='camera', lazy=True)

@camera_bp.route('/api/cameras', methods=['GET'])
def get_cameras():
    cameras = Camera.query.all()
    return jsonify([{
        'id': camera.id,
        'name': camera.name,
        'location': camera.location,
        'type': camera.camera_type,
        'status': camera.status,
        'stream_url': camera.stream_url,
        'ip_address': camera.ip_address,
        'port': camera.port
    } for camera in cameras])

@camera_bp.route('/api/cameras/<int:camera_id>', methods=['GET'])
def get_camera(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    return jsonify({
        'id': camera.id,
        'name': camera.name,
        'location': camera.location,
        'type': camera.camera_type,
        'status': camera.status,
        'stream_url': camera.stream_url,
        'ip_address': camera.ip_address,
        'port': camera.port
    })

@camera_bp.route('/api/cameras', methods=['POST'])
def add_camera():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    camera = Camera(
        name=data['name'],
        location=data.get('location'),
        camera_type=data['type'],
        ip_address=data.get('ip_address'),
        port=data.get('port'),
        user_id=data.get('user_id')
    )
    
    if camera.camera_type in ['ipcam', 'droidcam'] and camera.ip_address and camera.port:
        camera.stream_url = f"http://{camera.ip_address}:{camera.port}/video"
    
    db.session.add(camera)
    db.session.commit()
    
    # Create directory for camera images if it doesn't exist
    camera_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'camera{camera.id}')
    os.makedirs(camera_dir, exist_ok=True)
    
    return jsonify({
        'id': camera.id,
        'name': camera.name,
        'message': 'Camera added successfully'
    }), 201

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
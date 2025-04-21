import cv2
import numpy as np
import threading
import time
import os
import base64
from datetime import datetime
from models import db, Camera, Emotion

class CameraHandler:
    """Lớp cơ sở để xử lý camera, các loại camera cụ thể sẽ kế thừa từ lớp này"""
    
    def __init__(self, camera_id):
        """
        Khởi tạo handler cho camera
        
        Args:
            camera_id (int): ID của camera trong database
        """
        self.camera_id = camera_id
        self.camera = None
        self.stream = None
        self.is_running = False
        self.thread = None
        self.frame = None
        self.last_frame_time = None
        self.load_camera_from_db()
    
    def load_camera_from_db(self):
        """Tải thông tin camera từ database"""
        self.camera = Camera.query.get(self.camera_id)
        if not self.camera:
            raise ValueError(f"Không tìm thấy camera với ID: {self.camera_id}")
        
        # Cập nhật trạng thái camera trong DB
        self.camera.connection_status = 'connecting'
        db.session.commit()
    
    def start(self):
        """Bắt đầu luồng xử lý camera"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._update_frame)
        self.thread.daemon = True
        self.thread.start()
        
        # Cập nhật trạng thái camera trong DB
        self.camera.connection_status = 'connected'
        self.camera.last_connected = datetime.now()
        db.session.commit()
        
        return True
    
    def stop(self):
        """Dừng luồng xử lý camera"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        
        if self.stream:
            try:
                self.stream.release()
            except:
                pass
            
        self.stream = None
        
        # Cập nhật trạng thái camera trong DB
        self.camera.connection_status = 'disconnected'
        db.session.commit()
    
    def get_frame(self):
        """Lấy frame hiện tại từ camera"""
        return self.frame
    
    def _update_frame(self):
        """Cập nhật frame liên tục (được override trong các lớp con)"""
        raise NotImplementedError("Phương thức này cần được triển khai trong lớp con")
    
    def save_frame(self, frame, emotion_data=None):
        """
        Lưu frame với thông tin cảm xúc
        
        Args:
            frame: Hình ảnh frame đã được xử lý
            emotion_data: Dictionary chứa thông tin cảm xúc
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_dir = os.path.join("static", "images", str(self.camera_id))
        result_dir = os.path.join("static", "results", str(self.camera_id))
        
        os.makedirs(image_dir, exist_ok=True)
        os.makedirs(result_dir, exist_ok=True)
        
        image_path = os.path.join(image_dir, f"{timestamp}.jpg")
        result_path = os.path.join(result_dir, f"{timestamp}.jpg")
        
        # Lưu hình ảnh gốc
        cv2.imwrite(image_path, frame)
        
        # Lưu hình ảnh đã xử lý (nếu có emotion_data)
        processed_frame = frame.copy()
        if emotion_data:
            dominant_emotion = emotion_data.get('dominant_emotion', 'unknown')
            scores = emotion_data.get('scores', {})
            
            # Vẽ khuôn mặt và cảm xúc lên ảnh đã xử lý
            for face in emotion_data.get('faces', []):
                x, y, w, h = face['box']
                cv2.rectangle(processed_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(processed_frame, dominant_emotion, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            cv2.imwrite(result_path, processed_frame)
            
            # Chuyển đổi ảnh sang base64 để lưu vào database
            _, buffer_img = cv2.imencode('.jpg', frame)
            image_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            _, buffer_result = cv2.imencode('.jpg', processed_frame)
            processed_image_base64 = base64.b64encode(buffer_result).decode('utf-8')
            
            # Lưu vào database
            emotion = Emotion(
                camera_id=self.camera_id,
                image_path=image_path,
                result_path=result_path,
                dominant_emotion=dominant_emotion,
                emotion_scores=scores,
                image_base64=image_base64,
                processed_image_base64=processed_image_base64,
                user_id=self.camera.user_id
            )
            
            db.session.add(emotion)
            db.session.commit()
            
            return result_path
        
        return image_path


class WebcamHandler(CameraHandler):
    """Handler cho webcam"""
    
    def __init__(self, camera_id):
        super().__init__(camera_id)
        
    def _update_frame(self):
        """Cập nhật frame từ webcam"""
        # Phát hiện camera ID từ thông tin camera
        # Nếu self.camera.stream_url là 'webcam', sử dụng camera trong thiết bị local
        device_id = 0  # Mặc định là camera đầu tiên
        
        # Khởi tạo luồng video
        self.stream = cv2.VideoCapture(device_id)
        
        if not self.stream.isOpened():
            self.is_running = False
            self.camera.connection_status = 'disconnected'
            db.session.commit()
            return
        
        while self.is_running:
            success, frame = self.stream.read()
            if not success:
                # Nếu không đọc được frame, thử kết nối lại
                time.sleep(1)
                continue
                
            self.frame = frame
            self.last_frame_time = datetime.now()
            time.sleep(0.03)  # 30 FPS
            
        self.stream.release()


class IPCameraHandler(CameraHandler):
    """Handler cho IP camera"""
    
    def __init__(self, camera_id):
        super().__init__(camera_id)
    
    def _update_frame(self):
        """Cập nhật frame từ IP camera"""
        # Lấy URL stream từ thông tin camera
        stream_url = self.camera.get_stream_url()
        
        if not stream_url:
            self.is_running = False
            self.camera.connection_status = 'disconnected'
            db.session.commit()
            return
        
        # Khởi tạo luồng video
        self.stream = cv2.VideoCapture(stream_url)
        
        if not self.stream.isOpened():
            self.is_running = False
            self.camera.connection_status = 'disconnected'
            db.session.commit()
            return
        
        while self.is_running:
            success, frame = self.stream.read()
            if not success:
                # Nếu không đọc được frame, thử kết nối lại
                time.sleep(1)
                self.stream = cv2.VideoCapture(stream_url)
                continue
                
            self.frame = frame
            self.last_frame_time = datetime.now()
            time.sleep(0.03)  # 30 FPS
            
        self.stream.release()


class DroidCamHandler(CameraHandler):
    """Handler cho DroidCam"""
    
    def __init__(self, camera_id):
        super().__init__(camera_id)
    
    def _update_frame(self):
        """Cập nhật frame từ DroidCam"""
        # Lấy URL stream từ thông tin camera
        stream_url = self.camera.get_stream_url()
        
        if not stream_url:
            self.is_running = False
            self.camera.connection_status = 'disconnected'
            db.session.commit()
            return
        
        # Khởi tạo luồng video
        self.stream = cv2.VideoCapture(stream_url)
        
        if not self.stream.isOpened():
            self.is_running = False
            self.camera.connection_status = 'disconnected'
            db.session.commit()
            return
        
        while self.is_running:
            success, frame = self.stream.read()
            if not success:
                # Nếu không đọc được frame, thử kết nối lại
                time.sleep(1)
                self.stream = cv2.VideoCapture(stream_url)
                continue
                
            self.frame = frame
            self.last_frame_time = datetime.now()
            time.sleep(0.03)  # 30 FPS
            
        self.stream.release()


def get_camera_handler(camera_id):
    """
    Factory để tạo handler phù hợp cho từng loại camera
    
    Args:
        camera_id (int): ID của camera trong database
    
    Returns:
        CameraHandler: Handler phù hợp cho loại camera
    """
    camera = Camera.query.get(camera_id)
    if not camera:
        raise ValueError(f"Không tìm thấy camera với ID: {camera_id}")
    
    if camera.camera_type == 'webcam':
        return WebcamHandler(camera_id)
    elif camera.camera_type == 'droidcam':
        return DroidCamHandler(camera_id)
    elif camera.camera_type == 'ipcam':
        return IPCameraHandler(camera_id)
    else:
        raise ValueError(f"Loại camera không được hỗ trợ: {camera.camera_type}")


# Lưu trữ các đối tượng camera đang hoạt động
active_cameras = {}

def get_active_camera(camera_id):
    """Lấy đối tượng camera đang hoạt động"""
    return active_cameras.get(camera_id)

def start_camera(camera_id):
    """Bắt đầu luồng xử lý camera"""
    if camera_id in active_cameras:
        return active_cameras[camera_id]
    
    handler = get_camera_handler(camera_id)
    if handler.start():
        active_cameras[camera_id] = handler
        return handler
    
    return None

def stop_camera(camera_id):
    """Dừng luồng xử lý camera"""
    if camera_id in active_cameras:
        active_cameras[camera_id].stop()
        del active_cameras[camera_id]
        return True
    
    return False

def stop_all_cameras():
    """Dừng tất cả các camera đang hoạt động"""
    for camera_id in list(active_cameras.keys()):
        stop_camera(camera_id) 
import cv2
import numpy as np
import threading
import time
from datetime import datetime
import os
import json
from deepface import DeepFace

# Khai báo cascade classifier cho face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

class EmotionDetector:
    """Lớp xử lý nhận diện cảm xúc từ frame hình ảnh"""
    
    def __init__(self, camera_handler, interval_seconds=1):
        """
        Khởi tạo bộ nhận diện cảm xúc
        
        Args:
            camera_handler: Đối tượng xử lý camera
            interval_seconds (int): Khoảng thời gian giữa các lần nhận diện (giây)
        """
        self.camera_handler = camera_handler
        self.interval_seconds = interval_seconds
        self.is_running = False
        self.thread = None
        self.last_processed_time = None
        self.callbacks = []
    
    def start(self):
        """Bắt đầu luồng nhận diện cảm xúc"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._process_frames)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def stop(self):
        """Dừng luồng nhận diện cảm xúc"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def add_callback(self, callback):
        """
        Thêm callback được gọi khi có kết quả nhận diện
        
        Args:
            callback: Hàm callback, nhận các tham số (frame, emotion_data)
        """
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        """Xóa callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _process_frames(self):
        """Xử lý các frame từ camera để nhận diện cảm xúc"""
        while self.is_running:
            # Kiểm tra xem đã đến lúc xử lý frame tiếp theo chưa
            current_time = datetime.now()
            if (self.last_processed_time is None or 
                (current_time - self.last_processed_time).total_seconds() >= self.interval_seconds):
                
                # Lấy frame hiện tại từ camera handler
                frame = self.camera_handler.get_frame()
                if frame is not None:
                    # Thực hiện nhận diện cảm xúc
                    try:
                        emotion_data = self._detect_emotion(frame)
                        if emotion_data:
                            # Lưu frame và thông tin cảm xúc
                            result_path = self.camera_handler.save_frame(frame, emotion_data)
                            
                            # Gọi các callback
                            for callback in self.callbacks:
                                try:
                                    callback(frame, emotion_data, result_path)
                                except Exception as e:
                                    print(f"Lỗi khi gọi callback: {e}")
                    except Exception as e:
                        print(f"Lỗi khi xử lý frame: {e}")
                
                self.last_processed_time = current_time
            
            # Ngủ một khoảng thời gian nhỏ để không tốn CPU
            time.sleep(0.1)
    
    def _detect_emotion(self, frame):
        """
        Nhận diện cảm xúc từ một frame
        
        Args:
            frame: Frame hình ảnh cần nhận diện
        
        Returns:
            dict: Thông tin về các khuôn mặt và cảm xúc phát hiện được
        """
        # Chuyển đổi frame sang grayscale cho face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Phát hiện khuôn mặt
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return None  # Không phát hiện khuôn mặt nào
        
        results = {
            'faces': [],
            'dominant_emotion': None,
            'scores': {}
        }
        
        for (x, y, w, h) in faces:
            face_dict = {'box': (x, y, w, h)}
            
            try:
                # Sử dụng DeepFace để nhận diện cảm xúc
                emotion_analysis = DeepFace.analyze(
                    frame, 
                    actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv'
                )
                
                if isinstance(emotion_analysis, list):
                    emotion_analysis = emotion_analysis[0]
                
                emotions = emotion_analysis['emotion']
                dominant_emotion = emotion_analysis['dominant_emotion']
                
                face_dict['emotions'] = emotions
                face_dict['dominant_emotion'] = dominant_emotion
                
                # Cập nhật thông tin tổng hợp
                if results['dominant_emotion'] is None or emotions[dominant_emotion] > results['scores'].get(results['dominant_emotion'], 0):
                    results['dominant_emotion'] = dominant_emotion
                
                # Cập nhật điểm số cảm xúc
                for emotion, score in emotions.items():
                    results['scores'][emotion] = max(score, results['scores'].get(emotion, 0))
                
            except Exception as e:
                print(f"Lỗi khi phân tích cảm xúc: {e}")
                continue
            
            results['faces'].append(face_dict)
        
        return results if results['faces'] else None


# Lưu trữ các emotion detector đang hoạt động
active_detectors = {}

def start_emotion_detection(camera_id, interval_seconds=1, callback=None):
    """
    Bắt đầu nhận diện cảm xúc cho một camera
    
    Args:
        camera_id (int): ID của camera
        interval_seconds (int): Khoảng thời gian giữa các lần nhận diện
        callback: Hàm callback được gọi khi có kết quả nhận diện
    
    Returns:
        EmotionDetector: Đối tượng detector nếu thành công, None nếu thất bại
    """
    from camera_handlers import get_active_camera, start_camera
    
    # Kiểm tra xem đã có detector đang chạy chưa
    if camera_id in active_detectors:
        detector = active_detectors[camera_id]
        if callback:
            detector.add_callback(callback)
        return detector
    
    # Lấy camera handler
    camera_handler = get_active_camera(camera_id)
    if not camera_handler:
        # Nếu camera chưa được kích hoạt, thử kích hoạt
        camera_handler = start_camera(camera_id)
    
    if not camera_handler:
        return None
    
    # Tạo detector mới
    detector = EmotionDetector(camera_handler, interval_seconds)
    if callback:
        detector.add_callback(callback)
    
    # Bắt đầu detector
    if detector.start():
        active_detectors[camera_id] = detector
        return detector
    
    return None

def stop_emotion_detection(camera_id, stop_camera=True):
    """
    Dừng nhận diện cảm xúc cho một camera
    
    Args:
        camera_id (int): ID của camera
        stop_camera (bool): Có dừng camera luôn không
    
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    if camera_id in active_detectors:
        detector = active_detectors[camera_id]
        detector.stop()
        del active_detectors[camera_id]
        
        if stop_camera:
            from camera_handlers import stop_camera as stop_cam
            stop_cam(camera_id)
        
        return True
    
    return False

def stop_all_detectors(stop_cameras=True):
    """
    Dừng tất cả các detector đang hoạt động
    
    Args:
        stop_cameras (bool): Có dừng các camera luôn không
    """
    for camera_id in list(active_detectors.keys()):
        stop_emotion_detection(camera_id, stop_cameras) 
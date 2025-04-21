# Emotion Detection Backend

Backend service for facial emotion recognition using deep learning.

## Features

- Real-time emotion detection from webcam
- Image processing and analysis
- RESTful API endpoints
- SQLite database for storing results
- JWT authentication
- CORS support

## Requirements

- Python 3.8+
- Flask
- OpenCV
- TensorFlow
- SQLAlchemy
- Other dependencies listed in requirements.txt

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
- Copy `.env.example` to `.env`
- Update variables as needed

4. Initialize database:
```bash
python init_db.py
```

## Running the Server

Development mode:
```bash
flask run
```

Production mode:
```bash
python app.py
```

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - User login
- POST `/api/auth/refresh` - Refresh access token

### Emotion Detection
- POST `/api/detect-emotion` - Detect emotion from image
- GET `/api/emotions` - Get emotion history
- GET `/api/image/<id>` - Get original image
- GET `/api/processed-image/<id>` - Get processed image

## Directory Structure

```
backend/
├── app.py              # Main application file
├── models.py           # Database models
├── init_db.py          # Database initialization
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
└── camera*/           # Image storage directories
```

## Error Handling

The application includes comprehensive error handling for:
- Database operations
- Image processing
- Authentication
- API requests

## Security

- JWT-based authentication
- Password hashing
- CORS protection
- Environment variable configuration

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## Tính năng mới: Nhóm Camera và Nhận diện đa Camera

### Nhóm Camera
Hệ thống giờ đây hỗ trợ nhóm các camera thành các nhóm logic để dễ dàng quản lý và điều khiển. Mỗi nhóm camera có thể hoạt động độc lập và được cấu hình số lượng tối đa camera có thể hoạt động đồng thời.

#### Các API quản lý nhóm camera:

- **GET /api/camera-groups**: Lấy danh sách tất cả các nhóm camera.
- **GET /api/camera-groups/:id**: Lấy thông tin chi tiết một nhóm camera.
- **POST /api/camera-groups**: Tạo một nhóm camera mới.
- **PUT /api/camera-groups/:id**: Cập nhật thông tin nhóm camera.
- **DELETE /api/camera-groups/:id**: Xóa một nhóm camera.

#### Các API liên kết camera và nhóm:

- **PUT /api/cameras/:camera_id/group/:group_id**: Thêm camera vào nhóm.
- **DELETE /api/cameras/:camera_id/group**: Xóa camera khỏi nhóm.
- **PUT /api/cameras/:camera_id/priority**: Cập nhật mức độ ưu tiên của camera trong nhóm.

#### Các API quản lý nhóm camera:

- **POST /api/camera-groups/:id/connect**: Kết nối và xử lý tất cả camera trong một nhóm.
- **POST /api/camera-groups/:id/disconnect**: Ngắt kết nối tất cả camera trong một nhóm.
- **GET /api/camera-groups/:id/status**: Lấy trạng thái kết nối của tất cả camera trong một nhóm.
- **GET /api/camera-groups/:id/results**: Lấy kết quả xử lý mới nhất từ tất cả camera trong một nhóm.

### Hướng dẫn kết nối nhiều camera IP từ điện thoại

1. **Cài đặt ứng dụng camera IP trên điện thoại**:
   - Android: DroidCam, IP Webcam, etc.
   - iOS: EpocCam, iVCam, etc.

2. **Tạo nhóm camera**:
   ```
   POST /api/camera-groups
   {
     "name": "Camera IP từ điện thoại",
     "description": "Các camera IP từ điện thoại trong phòng họp",
     "max_concurrent_cameras": 8
   }
   ```

3. **Thêm camera IP vào hệ thống**:
   ```
   POST /api/cameras
   {
     "name": "iPhone Camera 1",
     "location": "Phòng họp 1",
     "camera_type": "ipcam",
     "ip_address": "192.168.1.100",
     "port": 8080,
     "camera_group_id": 2,
     "priority": 10
   }
   ```

4. **Kết nối và xử lý tất cả camera trong nhóm**:
   ```
   POST /api/camera-groups/2/connect
   ```

5. **Lấy kết quả từ tất cả camera đang hoạt động trong nhóm**:
   ```
   GET /api/camera-groups/2/results
   ```

### Cập nhật Cơ sở dữ liệu

Để cập nhật cơ sở dữ liệu với cấu trúc mới hỗ trợ nhóm camera, chạy script migration:

```
python migrate_camera_groups.py
```

Script này sẽ:
1. Tạo bảng `camera_groups` nếu chưa tồn tại
2. Thêm cột `camera_group_id` và `priority` vào bảng `cameras`
3. Tạo các nhóm camera mặc định
4. Di chuyển camera hiện có vào nhóm phù hợp 
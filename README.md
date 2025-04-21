# Hệ Thống Nhận Diện Cảm Xúc Khuôn Mặt (Python 3.12)

Dự án nhận diện cảm xúc khuôn mặt từ hình ảnh camera, sử dụng DeepFace và Flask làm backend, React làm frontend.

## Yêu cầu hệ thống

- Python 3.12
- Node.js 16.x trở lên
- PostgreSQL 12 trở lên

## Cài đặt và Chạy

### Backend

1. Vào thư mục backend:

```bash
cd project/backend
```

2. Tạo môi trường ảo Python (tùy chọn nhưng khuyến nghị):

```bash
python -m venv venv
# Kích hoạt môi trường ảo
# Trên Windows:
venv\Scripts\activate
# Trên macOS/Linux:
source venv/bin/activate
```

3. Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

4. Cài đặt và cấu hình PostgreSQL:
   - Cài đặt PostgreSQL trên máy của bạn nếu chưa có
   - Tạo cơ sở dữ liệu mới có tên `emotion_detection1.2` (hoặc tên khác nhưng cần thay đổi trong tệp .env)
   - Tạo tệp `.env` từ tệp mẫu `.env.example` và cập nhật thông tin kết nối cơ sở dữ liệu nếu cần

```bash
cp .env.example .env
```

5. Chạy ứng dụng backend:

```bash
python app.py
```

Backend sẽ chạy tại `http://localhost:5000`

### Frontend

1. Vào thư mục frontend:

```bash
cd project/frontend
```

2. Cài đặt các gói phụ thuộc:

```bash
npm install
```

3. Chạy ứng dụng:

```bash
npm start
```

Frontend sẽ chạy tại `http://localhost:3000`

## Lưu ý khi sử dụng Python 3.12

Dự án đã được cập nhật để hỗ trợ Python 3.12, bao gồm:

1. **Cập nhật các thư viện**:
   - Các thư viện trong `requirements.txt` đã được cập nhật lên phiên bản tương thích với Python 3.12
   - SQLAlchemy đã được cập nhật lên phiên bản 2.0 với cú pháp mới
   - DeepFace đã được cập nhật để hoạt động tốt hơn với Python 3.12

2. **Xử lý khả năng tương thích**:
   - Mã nguồn bao gồm xử lý ngoại lệ cho các trường hợp DeepFace không được cài đặt đúng
   - Thích ứng với API mới của DeepFace trong phiên bản 0.0.79+
   - Cập nhật mô hình dữ liệu SQLAlchemy để tương thích với SQLAlchemy 2.0

3. **Tài nguyên hệ thống**:
   - Python 3.12 cải thiện hiệu suất và giảm sử dụng bộ nhớ so với các phiên bản trước
   - Các tính năng mới của Python 3.12 như cải tiến typing và debugging được hỗ trợ

## Cấu trúc dự án

```
project/
├── backend/
│   ├── app.py                # Backend Flask
│   ├── requirements.txt      # Thư viện Python
│   ├── .env.example          # Mẫu cấu hình môi trường
│   └── image{n}/             # Thư mục lưu trữ ảnh cho mỗi camera
├── frontend/
│   ├── public/               # Tài nguyên tĩnh
│   ├── src/                  # Mã nguồn React
│   │   ├── components/       # Các component React
│   │   ├── App.js            # Component chính
│   │   └── index.js          # Điểm vào ứng dụng
│   └── package.json          # Cấu hình npm
└── README.md                 # Tài liệu này
```

## Các tính năng chính

1. **Nhận diện cảm xúc thời gian thực**:
   - Chụp ảnh từ camera và phân tích cảm xúc
   - Hiển thị kết quả phân tích cảm xúc trực quan

2. **Quản lý camera**:
   - Thêm, sửa, xóa các camera trong hệ thống
   - Tự động tạo thư mục lưu trữ cho camera mới
   - Hỗ trợ nhiều loại camera: webcam, DroidCam, IP camera, RTSP, MJPEG
   - Kiểm tra kết nối với camera trước khi sử dụng

3. **Xử lý video trực tiếp**:
   - Kết nối trực tiếp với camera IP (điện thoại) và xử lý video stream
   - Phát hiện cảm xúc từ video stream theo thời gian thực
   - Hỗ trợ đa luồng, cho phép xử lý nhiều camera cùng lúc
   - Lưu trữ kết quả phân tích tự động theo chu kỳ

4. **Lập lịch tự động**:
   - Lập lịch chụp ảnh tự động từ camera theo hai chế độ:
     - Định kỳ theo khoảng thời gian: Chụp ảnh sau mỗi X phút
     - Thời điểm cố định: Chụp ảnh vào giờ và phút được chỉ định
   - Quản lý và xóa lịch trình đã thiết lập
   - Tự động phân tích cảm xúc từ ảnh chụp theo lịch

5. **Lịch sử cảm xúc**:
   - Lưu trữ lịch sử phát hiện cảm xúc
   - Tìm kiếm và lọc theo camera hoặc loại cảm xúc

## Kết nối với IP Camera (Điện thoại)

Để sử dụng điện thoại làm camera, bạn có thể làm theo các bước sau:

1. **Cài đặt ứng dụng IP Camera trên điện thoại**:
   - Android: IP Webcam, DroidCam
   - iOS: EpocCam, iVCam

2. **Cấu hình camera trong ứng dụng**:
   - Mở ứng dụng IP Camera trên điện thoại
   - Kết nối điện thoại và máy tính vào cùng một mạng WiFi
   - Ghi lại địa chỉ IP và cổng mà ứng dụng cung cấp

3. **Thêm IP Camera vào hệ thống**:
   - Trong ứng dụng web, chọn "Thêm Camera"
   - Chọn loại camera là "IP Camera" hoặc "DroidCam"
   - Nhập địa chỉ IP và cổng từ ứng dụng điện thoại
   - Lưu cấu hình và kiểm tra kết nối

4. **Kết nối trực tiếp với camera**:
   - Trong danh sách camera, nhấn nút "Kết nối trực tiếp" cho camera IP
   - Hệ thống sẽ bắt đầu xử lý video từ camera và phát hiện cảm xúc
   - Kết quả phân tích sẽ được lưu vào cơ sở dữ liệu theo chu kỳ

## Giải quyết sự cố

1. **Lỗi cài đặt thư viện DeepFace**:
   - Nếu gặp lỗi khi cài đặt DeepFace, hãy thử cài đặt các gói phụ thuộc (tensorflow, keras) trước, sau đó cài đặt DeepFace

2. **Lỗi kết nối PostgreSQL**:
   - Kiểm tra thông tin kết nối trong tệp `.env`
   - Đảm bảo dịch vụ PostgreSQL đang chạy

3. **Lỗi truy cập camera**:
   - Đảm bảo camera được kết nối và hoạt động
   - Kiểm tra quyền truy cập camera trong trình duyệt

4. **Lỗi lịch trình camera**:
   - Nếu gặp lỗi "Không thể tải lịch trình camera", hãy đảm bảo đã khởi động lại cả frontend và backend
   - Kiểm tra bảng `camera_schedules` trong cơ sở dữ liệu đã được tạo
   - Đảm bảo API `/api/cameras/schedule` hoạt động bình thường

5. **Lỗi kết nối IP Camera**:
   - Đảm bảo điện thoại và máy tính kết nối cùng mạng WiFi
   - Kiểm tra tường lửa hoặc phần mềm bảo mật có thể chặn kết nối
   - Xác minh địa chỉ IP và cổng được cấu hình chính xác
   - Thử khởi động lại ứng dụng camera trên điện thoại

## Khởi động ứng dụng

**Trên Windows, sử dụng file batch:**

Chạy file `start_app.bat` để khởi động cả backend và frontend một lúc.

**Khởi động riêng từng thành phần:**

1. Khởi động Backend:
```
cd backend
python app.py
```

2. Khởi động Frontend:
```
cd frontend
npm start
```

# Cấu hình môi trường

Để thay đổi địa chỉ IP của server API:

1. **Môi trường phát triển**: Chỉnh sửa file `frontend/.env.development`
   ```
   REACT_APP_API_URL=http://localhost:5000
   ```

2. **Môi trường sản xuất**: Chỉnh sửa file `frontend/.env.production` trước khi build
   ```
   REACT_APP_API_URL=http://your-server-ip:5000
   ```

3. **Khi triển khai**: Có thể truyền biến môi trường trực tiếp khi chạy lệnh build
   ```
   REACT_APP_API_URL=http://171.224.199.63:5000 npm run build
   ``` 
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

3. **Lịch sử cảm xúc**:
   - Lưu trữ lịch sử phát hiện cảm xúc
   - Tìm kiếm và lọc theo camera

## Giải quyết sự cố

1. **Lỗi cài đặt thư viện DeepFace**:
   - Nếu gặp lỗi khi cài đặt DeepFace, hãy thử cài đặt các gói phụ thuộc (tensorflow, keras) trước, sau đó cài đặt DeepFace

2. **Lỗi kết nối PostgreSQL**:
   - Kiểm tra thông tin kết nối trong tệp `.env`
   - Đảm bảo dịch vụ PostgreSQL đang chạy

3. **Lỗi truy cập camera**:
   - Đảm bảo camera được kết nối và hoạt động
   - Kiểm tra quyền truy cập camera trong trình duyệt 
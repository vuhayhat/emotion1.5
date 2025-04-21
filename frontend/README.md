# Ứng dụng Nhận Diện Cảm Xúc - Frontend

Frontend cho hệ thống nhận diện cảm xúc khuôn mặt, sử dụng React.js và WebRTC để truy cập camera và gửi ảnh tới backend để phân tích.

## Cài đặt

### 1. Cài đặt các phụ thuộc

```bash
npm install
```

### 2. Cấu hình môi trường

Sao chép file `.env.example` thành file `.env`:

```bash
cp .env.example .env
```

Chỉnh sửa file `.env` để cấu hình URL API và các thông số khác:

```
REACT_APP_API_URL=http://địa-chỉ-server:cổng
REACT_APP_API_TIMEOUT=30000
REACT_APP_VERSION=1.0.0
REACT_APP_DEBUG=true
```

### 3. Chạy ứng dụng

```bash
npm start
```

Ứng dụng sẽ chạy ở địa chỉ [http://localhost:3000](http://localhost:3000)

## Dựng phiên bản production

```bash
npm run build
```

Để cấu hình URL API cho môi trường production, chỉnh sửa file `.env.production`

## Cấu trúc thư mục

```
frontend/
├── public/
│   ├── index.html
│   └── ...
├── src/
│   ├── components/
│   │   ├── CameraCapture.js    # Component xử lý camera và chụp ảnh
│   │   ├── EmotionHistory.js   # Component hiển thị lịch sử cảm xúc
│   │   └── Header.js           # Header của ứng dụng
│   ├── App.js                  # Component chính của ứng dụng
│   ├── index.js                # Điểm vào của ứng dụng
│   └── ...
├── package.json
└── README.md
```

## Tính năng

1. **Nhận diện cảm xúc qua camera**:
   - Chụp ảnh từ camera theo khoảng thời gian được cấu hình
   - Gửi ảnh đến backend để phân tích
   - Hiển thị kết quả phân tích cảm xúc

2. **Lựa chọn camera**:
   - Hỗ trợ nhiều thiết bị camera
   - Cho phép người dùng chọn camera để sử dụng

3. **Lịch sử cảm xúc**:
   - Hiển thị lịch sử nhận diện cảm xúc từ cơ sở dữ liệu
   - Hỗ trợ lọc theo camera
   - Phân trang kết quả

## Công nghệ

- React.js: Thư viện JavaScript để xây dựng giao diện người dùng
- WebRTC: Truy cập camera thông qua trình duyệt
- React Bootstrap: UI framework
- Axios: Thư viện HTTP client để giao tiếp với backend 

## Cấu hình API

Ứng dụng sử dụng các biến môi trường để cấu hình kết nối API:

- `REACT_APP_API_URL`: URL cơ sở của API server
- `REACT_APP_API_TIMEOUT`: Thời gian timeout cho các request API (ms)
- `REACT_APP_VERSION`: Phiên bản ứng dụng
- `REACT_APP_DEBUG`: Chế độ debug (true/false)

Các biến môi trường được đọc từ các tệp:
- `.env`: Biến môi trường cục bộ, không được commit lên git
- `.env.development`: Sử dụng cho môi trường phát triển (npm start)
- `.env.production`: Sử dụng cho bản build production (npm run build) 
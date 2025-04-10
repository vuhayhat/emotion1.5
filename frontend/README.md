# Frontend Nhận Diện Cảm Xúc Khuôn Mặt

Frontend cho hệ thống nhận diện cảm xúc khuôn mặt, sử dụng React.js và WebRTC để truy cập camera và gửi ảnh tới backend để phân tích.

## Cài đặt

1. Cài đặt các gói phụ thuộc:

```bash
npm install
```

2. Chạy ứng dụng trong môi trường phát triển:

```bash
npm start
```

Ứng dụng sẽ chạy tại [http://localhost:3000](http://localhost:3000).

## Cấu hình

- Mặc định, ứng dụng kết nối tới backend tại `http://localhost:5000`.
- Nếu bạn cần thay đổi địa chỉ API, hãy chỉnh sửa biến `apiEndpoint` trong các component liên quan.

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
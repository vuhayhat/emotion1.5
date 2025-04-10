import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Row, Col, Card, Button, Form, Alert, ProgressBar, Spinner, Badge } from 'react-bootstrap';
import Webcam from 'react-webcam';
import axios from 'axios';

// Định nghĩa các màu cho các cảm xúc
const emotionColors = {
  angry: '#dc3545',
  disgust: '#6f42c1',
  fear: '#fd7e14',
  happy: '#28a745',
  sad: '#17a2b8',
  surprise: '#ffc107',
  neutral: '#6c757d'
};

// Ánh xạ tên cảm xúc sang tiếng Việt
const emotionLabels = {
  angry: 'Giận dữ',
  disgust: 'Ghê tởm',
  fear: 'Sợ hãi',
  happy: 'Vui vẻ',
  sad: 'Buồn bã',
  surprise: 'Ngạc nhiên',
  neutral: 'Bình thường'
};

// Các độ phân giải camera tối ưu
const CAMERA_RESOLUTIONS = [
  { label: 'Thấp (320x240)', width: 320, height: 240 },
  { label: 'Trung bình (640x480)', width: 640, height: 480 },
  { label: 'Cao (1280x720)', width: 1280, height: 720 },
  { label: 'Full HD (1920x1080)', width: 1920, height: 1080 },
];

const CameraCapture = () => {
  const webcamRef = useRef(null);
  const [captureInterval, setCaptureInterval] = useState(2); // Giảm thời gian mặc định xuống 2 giây
  const [isRunning, setIsRunning] = useState(false);
  const [cameraId, setCameraId] = useState(1);
  const [webcamDevices, setWebcamDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [emotionResult, setEmotionResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingCameras, setLoadingCameras] = useState(false);
  const intervalRef = useRef(null);
  const [registeredCameras, setRegisteredCameras] = useState([]);
  const [debugInfo, setDebugInfo] = useState(false); // Thêm chế độ debug
  const [captureCount, setCaptureCount] = useState(0); // Đếm số ảnh đã chụp
  const [successCount, setSuccessCount] = useState(0); // Đếm số lần nhận diện thành công
  const [lastProcessingTime, setLastProcessingTime] = useState(0); // Thời gian xử lý cuối cùng

  // Chất lượng webcam
  const [selectedResolution, setSelectedResolution] = useState(2); // Mặc định là cao 1280x720
  const [webcamWidth, setWebcamWidth] = useState(CAMERA_RESOLUTIONS[2].width);
  const [webcamHeight, setWebcamHeight] = useState(CAMERA_RESOLUTIONS[2].height);

  // API endpoint
  const API_URL = 'http://localhost:5000/api';

  // Lấy danh sách thiết bị camera
  useEffect(() => {
    const getCameraDevices = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        setWebcamDevices(videoDevices);
        
        if (videoDevices.length > 0) {
          setSelectedDevice(videoDevices[0].deviceId);
        }
      } catch (err) {
        console.error('Không thể lấy danh sách thiết bị camera:', err);
        setError('Không thể truy cập camera. Vui lòng kiểm tra quyền truy cập.');
      }
    };

    getCameraDevices();
  }, []);

  // Lấy danh sách camera đã đăng ký
  useEffect(() => {
    const fetchRegisteredCameras = async () => {
      try {
        setLoadingCameras(true);
        const response = await axios.get(`${API_URL}/cameras`);
        
        // Lọc ra các camera đang hoạt động
        const activeCameras = (response.data.cameras || []).filter(cam => cam.is_active);
        
        setRegisteredCameras(activeCameras);
        
        // Nếu đã đăng ký camera và đang không chọn camera nào, mặc định chọn camera đầu tiên
        if (activeCameras.length > 0 && !cameraId) {
          setCameraId(activeCameras[0].id);
        }
      } catch (err) {
        console.error('Lỗi khi tải danh sách camera đã đăng ký:', err);
      } finally {
        setLoadingCameras(false);
      }
    };
    
    fetchRegisteredCameras();
  }, []);

  // Xử lý khi thay đổi độ phân giải
  const handleResolutionChange = (e) => {
    const resIndex = parseInt(e.target.value);
    setSelectedResolution(resIndex);
    const resolution = CAMERA_RESOLUTIONS[resIndex];
    setWebcamWidth(resolution.width);
    setWebcamHeight(resolution.height);
    
    // Nếu đang chạy, chụp một hình ảnh mới ngay lập tức để cập nhật với độ phân giải mới
    if (isRunning) {
      setTimeout(captureImage, 500);
    }
  };

  // Xử lý chụp ảnh từ webcam
  const captureImage = useCallback(async () => {
    if (webcamRef.current) {
      try {
        setLoading(true);
        setCaptureCount(prev => prev + 1);
        
        // Lấy hình ảnh từ webcam - bắt đầu đo hiệu suất
        const startTime = performance.now();
        const imageSrc = webcamRef.current.getScreenshot();
        
        if (!imageSrc) {
          throw new Error('Không thể chụp ảnh từ camera');
        }

        if (debugInfo) {
          console.log(`Chụp ảnh với độ phân giải ${webcamWidth}x${webcamHeight}`);
          
          // Tính toán kích thước ảnh 
          const base64Size = (imageSrc.length * 3) / 4 - 2;
          console.log(`Kích thước ảnh: ${(base64Size / 1024).toFixed(2)} KB`);
        }

        // Gửi ảnh lên server và đo thời gian
        const response = await axios.post(`${API_URL}/detect-emotion`, {
          image: imageSrc,
          cameraId: cameraId
        });

        const endTime = performance.now();
        const processingTime = endTime - startTime;
        setLastProcessingTime(processingTime);

        if (debugInfo) {
          console.log('Kết quả nhận diện:', response.data);
          console.log(`Thời gian xử lý: ${processingTime.toFixed(2)}ms`);
        }
        
        setEmotionResult(response.data);
        setSuccessCount(prev => prev + 1);
        setError('');
      } catch (err) {
        console.error('Lỗi khi xử lý ảnh:', err);
        setError(err.response?.data?.error || err.message || 'Có lỗi xảy ra khi phân tích cảm xúc');
      } finally {
        setLoading(false);
      }
    }
  }, [webcamRef, cameraId, API_URL, webcamWidth, webcamHeight, debugInfo]);

  // Bắt đầu/dừng nhận diện
  const toggleCapture = () => {
    if (isRunning) {
      // Dừng chụp
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setIsRunning(false);
    } else {
      // Bắt đầu chụp
      captureImage(); // Chụp ngay lập tức
      intervalRef.current = setInterval(() => {
        captureImage();
      }, captureInterval * 1000);
      setIsRunning(true);
    }
  };

  // Xử lý thay đổi khoảng thời gian
  const handleIntervalChange = (e) => {
    const value = parseInt(e.target.value);
    if (value > 0) {
      setCaptureInterval(value);
      // Nếu đang chạy, khởi động lại với khoảng thời gian mới
      if (isRunning && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = setInterval(captureImage, value * 1000);
      }
    }
  };

  // Dọn dẹp khi component unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Lấy tên camera từ ID
  const getCameraNameById = (id) => {
    const camera = registeredCameras.find(cam => cam.id === id);
    if (camera) {
      return camera.name;
    }
    return `Camera ${id}`;
  };

  // Reset đếm
  const resetCounters = () => {
    setCaptureCount(0);
    setSuccessCount(0);
  };

  return (
    <div>
      <Row className="mb-4">
        <Col md={8}>
          <Card className="camera-container shadow">
            <Card.Body>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h4 className="mb-0">{getCameraNameById(cameraId)}</h4>
                <div className="camera-status">
                  {isRunning ? (
                    <Badge bg="success" className="pulse-badge">Đang nhận diện</Badge>
                  ) : (
                    <Badge bg="secondary">Đã dừng</Badge>
                  )}
                </div>
              </div>
              
              <div className="webcam-container">
                <Webcam
                  audio={false}
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  screenshotQuality={1}
                  className="camera-view"
                  width={webcamWidth}
                  height={webcamHeight}
                  videoConstraints={{
                    deviceId: selectedDevice,
                    width: { ideal: webcamWidth },
                    height: { ideal: webcamHeight }
                  }}
                />
                {loading && (
                  <div className="webcam-overlay">
                    <Spinner animation="border" variant="light" />
                  </div>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={4}>
          <Card className="control-panel shadow">
            <Card.Header className="bg-primary text-white">
              <h5 className="mb-0">Bảng điều khiển</h5>
            </Card.Header>
            <Card.Body>
              {error && (
                <Alert variant="danger" dismissible onClose={() => setError('')}>
                  {error}
                </Alert>
              )}
              
              <Form.Group className="mb-3">
                <Form.Label>Camera</Form.Label>
                <Form.Select 
                  value={cameraId}
                  onChange={(e) => setCameraId(parseInt(e.target.value))}
                  disabled={isRunning || loadingCameras}
                >
                  {loadingCameras ? (
                    <option>Đang tải camera...</option>
                  ) : (
                    registeredCameras.length > 0 ? (
                      registeredCameras.map(camera => (
                        <option key={camera.id} value={camera.id}>
                          {camera.name}
                        </option>
                      ))
                    ) : (
                      <option value={1}>Camera 1</option>
                    )
                  )}
                </Form.Select>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>Thiết bị</Form.Label>
                <Form.Select
                  value={selectedDevice}
                  onChange={(e) => setSelectedDevice(e.target.value)}
                  disabled={isRunning}
                >
                  {webcamDevices.map((device, index) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || `Camera ${index + 1}`}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>Độ phân giải</Form.Label>
                <Form.Select
                  value={selectedResolution}
                  onChange={handleResolutionChange}
                >
                  {CAMERA_RESOLUTIONS.map((res, index) => (
                    <option key={index} value={index}>
                      {res.label}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>
                  Thời gian chụp (giây): {captureInterval}
                </Form.Label>
                <Form.Range
                  min={1}
                  max={10}
                  step={1}
                  value={captureInterval}
                  onChange={handleIntervalChange}
                />
              </Form.Group>
              
              <div className="d-grid">
                <Button
                  variant={isRunning ? "danger" : "success"}
                  className="mb-3"
                  onClick={toggleCapture}
                  disabled={loading}
                >
                  {isRunning ? "Dừng nhận diện" : "Bắt đầu nhận diện"}
                </Button>
              </div>
              
              <Form.Check 
                type="switch"
                id="debug-switch"
                label="Hiển thị thông tin debug"
                checked={debugInfo}
                onChange={() => setDebugInfo(!debugInfo)}
                className="mb-3"
              />
              
              {debugInfo && (
                <div className="debug-info p-2 bg-light rounded mb-3">
                  <small>
                    <div><strong>Độ phân giải:</strong> {webcamWidth}x{webcamHeight}</div>
                    <div><strong>Số ảnh đã chụp:</strong> {captureCount}</div>
                    <div><strong>Nhận diện thành công:</strong> {successCount}</div>
                    <div><strong>Tỉ lệ thành công:</strong> {captureCount > 0 ? ((successCount / captureCount) * 100).toFixed(1) : 0}%</div>
                    <div><strong>Thời gian xử lý:</strong> {lastProcessingTime.toFixed(0)}ms</div>
                    <div className="mt-1">
                      <Button size="sm" variant="outline-secondary" onClick={resetCounters}>Reset</Button>
                    </div>
                  </small>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {emotionResult && (
        <Row>
          <Col md={12}>
            <Card className="result-container shadow">
              <Card.Header className="bg-dark text-white">
                <h5 className="mb-0">Kết quả nhận diện cảm xúc</h5>
              </Card.Header>
              <Card.Body>
                <Row>
                  <Col md={6}>
                    {emotionResult.processed_image && (
                      <div className="text-center">
                        <h6>Hình ảnh đã xử lý</h6>
                        <div className="processed-image-container">
                          <img 
                            src={`data:image/jpeg;base64,${emotionResult.processed_image}`}
                            alt="Processed" 
                            className="img-fluid processed-image"
                          />
                        </div>
                      </div>
                    )}
                  </Col>
                  <Col md={6}>
                    <h6>Phân tích cảm xúc</h6>
                    <div className="emotion-summary p-2 mb-3 rounded" style={{
                      backgroundColor: emotionColors[emotionResult.dominant_emotion] + '22',
                      borderLeft: `4px solid ${emotionColors[emotionResult.dominant_emotion]}`
                    }}>
                      <div className="fs-5 fw-bold">
                        Cảm xúc chính: {emotionLabels[emotionResult.dominant_emotion] || emotionResult.dominant_emotion}
                      </div>
                      <div>
                        {new Date(emotionResult.timestamp).toLocaleString('vi-VN')}
                      </div>
                    </div>
                    
                    <div className="emotion-bars">
                      {Object.entries(emotionResult.emotion_percent || {}).sort((a, b) => b[1] - a[1]).map(([emotion, percent]) => (
                        <div key={emotion} className="mb-2">
                          <div className="d-flex justify-content-between align-items-center mb-1">
                            <div>{emotionLabels[emotion] || emotion}</div>
                            <div><strong>{percent}%</strong></div>
                          </div>
                          <ProgressBar 
                            now={percent} 
                            variant={emotion === 'angry' ? 'danger' : 
                                    emotion === 'happy' ? 'success' : 
                                    emotion === 'sad' ? 'info' : 
                                    emotion === 'surprise' ? 'warning' : 
                                    emotion === 'fear' ? 'primary' : 
                                    emotion === 'disgust' ? 'dark' : 'secondary'}
                          />
                        </div>
                      ))}
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default CameraCapture; 
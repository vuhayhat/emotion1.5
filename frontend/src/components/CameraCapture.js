import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Row, Col, Card, Button, Form, Alert, ProgressBar, Spinner, Badge, Tabs, Tab, Image, Container } from 'react-bootstrap';
import Webcam from 'react-webcam';
import apiService from '../services/api';

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
  
  // Quản lý đa camera
  const [activeCameras, setActiveCameras] = useState({
    webcam: true,
    ipcam1: false,
    ipcam2: false,
    ipcam3: false
  });
  
  // Chọn camera
  const [selectedCameras, setSelectedCameras] = useState({
    webcam: null, // Webcam mặc định
    ipcam1: null, // IP camera 1
    ipcam2: null, // IP camera 2
    ipcam3: null  // IP camera 3
  });
  
  // Kết quả cảm xúc cho từng camera
  const [cameraResults, setCameraResults] = useState({
    webcam: null,
    ipcam1: null,
    ipcam2: null,
    ipcam3: null
  });

  // Trạng thái kết nối camera
  const [cameraStatuses, setCameraStatuses] = useState({});
  
  // Chất lượng webcam
  const [selectedResolution, setSelectedResolution] = useState(2); // Mặc định là cao 1280x720
  const [webcamWidth, setWebcamWidth] = useState(CAMERA_RESOLUTIONS[2].width);
  const [webcamHeight, setWebcamHeight] = useState(CAMERA_RESOLUTIONS[2].height);

  // Lấy danh sách thiết bị camera
  useEffect(() => {
    const getCameraDevices = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        setWebcamDevices(videoDevices);
        
        if (videoDevices.length > 0) {
          setSelectedDevice(videoDevices[0].deviceId);
          setSelectedCameras(prev => ({...prev, webcam: videoDevices[0].deviceId}));
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
        const response = await apiService.cameras.getAll();
        setRegisteredCameras(response.data);
        
        // Tự động thiết lập IP cameras nếu có
        if (response.data.length > 0) {
          const ipCameras = response.data.filter(cam => cam.type === 'ipcam');
          
          // Thiết lập các IP camera mặc định
          const newSelectedCameras = {...selectedCameras};
          ipCameras.forEach((cam, index) => {
            if (index < 3) { // Chỉ hỗ trợ tối đa 3 IP camera
              const key = `ipcam${index + 1}`;
              newSelectedCameras[key] = cam.id;
            }
          });
          
          setSelectedCameras(newSelectedCameras);
        }
      } catch (err) {
        console.error('Lỗi khi lấy danh sách camera:', err);
        setError('Không thể lấy danh sách camera đã đăng ký');
      } finally {
        setLoadingCameras(false);
      }
    };

    fetchRegisteredCameras();
  }, []);

  // Xử lý thay đổi độ phân giải
  const handleResolutionChange = (e) => {
    const resIndex = parseInt(e.target.value);
    setSelectedResolution(resIndex);
    setWebcamWidth(CAMERA_RESOLUTIONS[resIndex].width);
    setWebcamHeight(CAMERA_RESOLUTIONS[resIndex].height);
  };

  // Xử lý thay đổi thời gian chụp
  const handleIntervalChange = (e) => {
    setCaptureInterval(parseInt(e.target.value));
  };

  // Xử lý chụp ảnh từ các camera
  const captureImage = useCallback(async () => {
    try {
      setLoading(true);
      setCaptureCount(prev => prev + 1);
      const startTime = performance.now();
      
      // Chụp từ webcam nếu đang kích hoạt
      if (activeCameras.webcam && webcamRef.current) {
        const imageSrc = webcamRef.current.getScreenshot();
        
        if (!imageSrc) {
          console.error('Không thể chụp ảnh từ webcam');
        } else {
          // Gửi ảnh lên server để nhận diện
          try {
            const response = await apiService.emotions.detect({
              image: imageSrc,
              cameraId: 'webcam',
              cameraName: 'Webcam'
            });
            
            setCameraResults(prev => ({
              ...prev,
              webcam: response.data
            }));
            
            setSuccessCount(prev => prev + 1);
          } catch (err) {
            console.error('Lỗi khi nhận diện cảm xúc từ webcam:', err);
          }
        }
      }
      
      // Xử lý các IP camera
      const ipCamKeys = ['ipcam1', 'ipcam2', 'ipcam3'];
      for (const key of ipCamKeys) {
        if (activeCameras[key] && selectedCameras[key]) {
          try {
            const cameraId = selectedCameras[key];
            const camera = registeredCameras.find(cam => cam.id === cameraId);
            
            if (!camera) continue;
            
            // Gửi yêu cầu chụp ảnh từ IP camera
            const response = await apiService.cameras.captureFromRTSP({
              url: camera.rtsp_url,
              cameraId: camera.id,
              cameraName: camera.name
            });
            
            if (response.data.success) {
              // Nhận diện cảm xúc từ ảnh đã chụp
              const emotionResponse = await apiService.emotions.detect({
                imageId: response.data.imageId,
                cameraId: camera.id,
                cameraName: camera.name
              });
              
              setCameraResults(prev => ({
                ...prev,
                [key]: emotionResponse.data
              }));
              
              setSuccessCount(prev => prev + 1);
            }
          } catch (err) {
            console.error(`Lỗi khi xử lý camera ${key}:`, err);
            setCameraResults(prev => ({
              ...prev,
              [key]: { error: err.message || 'Lỗi khi xử lý' }
            }));
          }
        }
      }
      
      const endTime = performance.now();
      setLastProcessingTime(endTime - startTime);
      
    } catch (err) {
      console.error('Lỗi khi chụp ảnh:', err);
      setError('Lỗi khi chụp ảnh: ' + (err.message || 'Lỗi không xác định'));
    } finally {
      setLoading(false);
    }
  }, [activeCameras, selectedCameras, webcamRef, registeredCameras]);

  // Khởi động/dừng việc chụp ảnh
  const toggleCapture = () => {
    if (isRunning) {
      // Dừng việc chụp liên tục
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setIsRunning(false);
    } else {
      // Khởi động việc chụp liên tục
      setIsRunning(true);
      captureImage(); // Chụp ngay lập tức
      
      // Thiết lập interval để chụp liên tục
      intervalRef.current = setInterval(() => {
        captureImage();
      }, captureInterval * 1000);
    }
  };

  // Cleanup khi component unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Toggle camera (bật/tắt)
  const toggleCamera = (cameraKey) => {
    setActiveCameras(prev => ({
      ...prev,
      [cameraKey]: !prev[cameraKey]
    }));
  };

  // Thay đổi camera được chọn
  const handleCameraChange = (cameraKey, cameraId) => {
    setSelectedCameras(prev => ({
      ...prev,
      [cameraKey]: cameraId
    }));
  };

  // Lấy tên camera từ ID
  const getCameraNameById = (cameraId) => {
    const camera = registeredCameras.find(cam => cam.id === cameraId);
    if (camera) {
      return camera.name;
    }
    
    if (cameraId === 'webcam') return 'Webcam';
    return `Camera ${cameraId}`;
  };

  // Reset đếm
  const resetCounters = () => {
    setCaptureCount(0);
    setSuccessCount(0);
  };

  // Xử lý mở trang quản lý camera
  const handleManageCameras = () => {
    window.location.href = '/quanlycam';
  };

  // Hiển thị kết quả cảm xúc
  const renderEmotionResult = (result) => {
    if (!result) return null;
    if (result.error) return <Alert variant="danger">{result.error}</Alert>;
    
    const emotion = result.emotion || {};
    const dominantEmotion = emotion.dominant_emotion || 'neutral';
    
    return (
      <div className="emotion-result">
        <h5>Kết quả:</h5>
        <div className="emotion-bars">
          {Object.entries(emotion.emotion || {}).map(([emo, score]) => (
            <div key={emo} className="emotion-bar-container">
              <div className="emotion-label">{emotionLabels[emo] || emo}</div>
              <ProgressBar
                now={score * 100}
                variant={emo === dominantEmotion ? 'success' : 'primary'}
                label={`${(score * 100).toFixed(1)}%`}
                className="emotion-bar"
              />
            </div>
          ))}
        </div>
        {result.image_url && (
          <div className="mt-2 text-center">
            <Image src={result.image_url} alt="Kết quả phân tích" thumbnail className="result-image" />
          </div>
        )}
      </div>
    );
  };

  // Render camera view
  const renderCameraView = (cameraKey) => {
    // Hiển thị webcam
    if (cameraKey === 'webcam') {
      return (
        <div className="camera-container">
          <Card className="shadow mb-4">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <div>
                <i className="bi bi-camera-video me-2"></i>
                Webcam
              </div>
              <Button 
                variant={activeCameras.webcam ? "danger" : "success"} 
                size="sm"
                onClick={() => toggleCamera('webcam')}
              >
                {activeCameras.webcam ? "Tắt Camera" : "Bật Camera"}
              </Button>
            </Card.Header>
            <Card.Body className="p-0">
              {activeCameras.webcam ? (
                <div className="webcam-container">
                  <Webcam
                    audio={false}
                    ref={webcamRef}
                    screenshotFormat="image/jpeg"
                    screenshotQuality={1}
                    className="camera-view"
                    width="100%"
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
              ) : (
                <div className="camera-placeholder">
                  <i className="bi bi-camera-video-off"></i>
                  <p>Camera tắt</p>
                </div>
              )}
            </Card.Body>
            <Card.Footer>
              {renderEmotionResult(cameraResults.webcam)}
            </Card.Footer>
          </Card>
        </div>
      );
    }
    
    // Hiển thị IP camera
    const cameraId = selectedCameras[cameraKey];
    const camera = registeredCameras.find(cam => cam.id === cameraId);
    const cameraName = camera ? camera.name : `IP Camera ${cameraKey.slice(-1)}`;
    
    return (
      <div className="camera-container">
        <Card className="shadow mb-4">
          <Card.Header className="d-flex justify-content-between align-items-center">
            <div>
              <i className="bi bi-camera me-2"></i>
              {cameraName}
            </div>
            <Button 
              variant={activeCameras[cameraKey] ? "danger" : "success"} 
              size="sm"
              onClick={() => toggleCamera(cameraKey)}
              disabled={!cameraId}
            >
              {activeCameras[cameraKey] ? "Tắt Camera" : "Bật Camera"}
            </Button>
          </Card.Header>
          <Card.Body className="p-0">
            {cameraId && activeCameras[cameraKey] ? (
              <div className="ipcam-container">
                {cameraResults[cameraKey]?.image_url ? (
                  <img 
                    src={cameraResults[cameraKey].image_url} 
                    alt={cameraName} 
                    className="camera-view" 
                  />
                ) : (
                  <div className="camera-placeholder">
                    <i className="bi bi-camera"></i>
                    <p>Đang chờ hình ảnh...</p>
                  </div>
                )}
                {loading && (
                  <div className="webcam-overlay">
                    <Spinner animation="border" variant="light" />
                  </div>
                )}
              </div>
            ) : (
              <div className="camera-placeholder">
                {!cameraId ? (
                  <>
                    <i className="bi bi-exclamation-triangle"></i>
                    <p>Chưa chọn camera</p>
                  </>
                ) : (
                  <>
                    <i className="bi bi-camera-video-off"></i>
                    <p>Camera tắt</p>
                  </>
                )}
              </div>
            )}
          </Card.Body>
          <Card.Footer>
            <Form.Group className="mb-3">
              <Form.Select 
                value={cameraId || ''} 
                onChange={(e) => handleCameraChange(cameraKey, e.target.value)}
                disabled={isRunning}
              >
                <option value="">Chọn camera</option>
                {registeredCameras.filter(cam => cam.type === 'ipcam').map(camera => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name} - {camera.rtsp_url}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            {renderEmotionResult(cameraResults[cameraKey])}
          </Card.Footer>
        </Card>
      </div>
    );
  };

  return (
    <Container fluid>
      <Row className="mb-4">
        <Col>
          <Card className="shadow">
            <Card.Header className="bg-primary text-white">
              <h5 className="mb-0">Nhận Diện Cảm Xúc</h5>
            </Card.Header>
            <Card.Body>
              <div className="controls mb-3">
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Thời gian chụp (giây): {captureInterval}</Form.Label>
                      <Form.Range
                        min={1}
                        max={10}
                        step={1}
                        value={captureInterval}
                        onChange={handleIntervalChange}
                        disabled={isRunning}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={3}>
                    <Form.Group className="mb-3">
                      <Form.Label>Độ phân giải</Form.Label>
                      <Form.Select
                        value={selectedResolution}
                        onChange={handleResolutionChange}
                        disabled={isRunning}
                      >
                        {CAMERA_RESOLUTIONS.map((res, index) => (
                          <option key={index} value={index}>
                            {res.label}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col md={3} className="d-flex align-items-end">
                    <div className="d-grid w-100">
                      <Button 
                        variant={isRunning ? "danger" : "success"} 
                        onClick={toggleCapture}
                        className="mb-3"
                      >
                        {isRunning ? (
                          <>
                            <i className="bi bi-stop-circle me-2"></i>
                            Dừng Chụp
                          </>
                        ) : (
                          <>
                            <i className="bi bi-play-circle me-2"></i>
                            Bắt Đầu Chụp
                          </>
                        )}
                      </Button>
                    </div>
                  </Col>
                </Row>
                <Row>
                  <Col>
                    <Button 
                      variant="outline-primary" 
                      onClick={handleManageCameras}
                      className="me-2"
                    >
                      <i className="bi bi-camera me-2"></i>
                      Quản Lý Camera
                    </Button>
                    <Button 
                      variant="outline-secondary" 
                      onClick={resetCounters}
                      className="me-2"
                    >
                      <i className="bi bi-arrow-counterclockwise me-2"></i>
                      Reset Đếm
                    </Button>
                    <Button 
                      variant="outline-info" 
                      onClick={() => setDebugInfo(!debugInfo)}
                    >
                      <i className="bi bi-bug me-2"></i>
                      {debugInfo ? 'Ẩn Debug' : 'Hiện Debug'}
                    </Button>
                  </Col>
                </Row>
                {debugInfo && (
                  <Row className="mt-3">
                    <Col>
                      <Alert variant="info">
                        <div>Số ảnh đã chụp: {captureCount}</div>
                        <div>Số lần nhận diện thành công: {successCount}</div>
                        <div>Thời gian xử lý cuối: {lastProcessingTime.toFixed(0)} ms</div>
                      </Alert>
                    </Col>
                  </Row>
                )}
                {error && (
                  <Row className="mt-3">
                    <Col>
                      <Alert variant="danger" onClose={() => setError('')} dismissible>
                        {error}
                      </Alert>
                    </Col>
                  </Row>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row>
        <Col md={6}>
          {renderCameraView('webcam')}
        </Col>
        <Col md={6}>
          {renderCameraView('ipcam1')}
        </Col>
      </Row>
      <Row>
        <Col md={6}>
          {renderCameraView('ipcam2')}
        </Col>
        <Col md={6}>
          {renderCameraView('ipcam3')}
        </Col>
      </Row>
    </Container>
  );
};

export default CameraCapture; 
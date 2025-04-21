import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Button, Spinner, Alert, Badge, Form, Image } from 'react-bootstrap';
import apiService from '../services/api';
import CameraSettings from './CameraSettings';
import CameraPlaceholder from './CameraPlaceholder';
import './MultipleCameraView.css';  // Thêm import CSS

const MultipleCameraView = () => {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeCameras, setActiveCameras] = useState({});
  const videoRefs = useRef({});
  const [refreshInterval, setRefreshInterval] = useState(3000); // Default 3 seconds
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [cameraGrid, setCameraGrid] = useState('3'); // Số camera trên một hàng: 2, 3, 4
  const [emotionResults, setEmotionResults] = useState({});
  const [showEmotionOverlay, setShowEmotionOverlay] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [cameraSettings, setCameraSettings] = useState({});
  const [isDetecting, setIsDetecting] = useState({});
  const [activeStates, setActiveStates] = useState({});
  const [loadingStates, setLoadingStates] = useState({});

  // Format timestamp to readable format
  const formatDateTime = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('vi-VN');
  };

  // Render connection status badge
  const renderConnectionStatus = (status) => {
    if (!status) return <Badge bg="secondary">Không xác định</Badge>;
    
    switch(status.toLowerCase()) {
      case 'connected':
        return <Badge bg="success">Kết nối</Badge>;
      case 'disconnected':
        return <Badge bg="danger">Ngắt kết nối</Badge>;
      case 'connecting':
        return <Badge bg="warning">Đang kết nối...</Badge>;
      case 'error':
        return <Badge bg="danger">Lỗi</Badge>;
      default:
        return <Badge bg="secondary">{status}</Badge>;
    }
  };

  // Fetch camera list - đưa ra ngoài useEffect để có thể gọi ở nơi khác
  const fetchCameras = async () => {
    try {
      setLoading(true);
      const response = await apiService.cameras.getAll();
      if (response.data) {
        setCameras(response.data.cameras || []);
        // Lấy trạng thái của tất cả camera
        const states = {};
        for (const camera of response.data.cameras) {
          try {
            const statusResponse = await apiService.cameras.getStatus(camera.id);
            states[camera.id] = statusResponse.data.is_active;
          } catch (error) {
            console.error(`Error getting status for camera ${camera.id}:`, error);
            states[camera.id] = false;
          }
        }
        setActiveStates(states);
      }
    } catch (error) {
      setError('Không thể tải danh sách camera');
      console.error('Error fetching cameras:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch camera list on component mount
  useEffect(() => {
    fetchCameras();
  }, []);

  // Add WebSocket connection for realtime emotion updates
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:5000/ws/emotion');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEmotionResults(prev => ({
        ...prev,
        [data.camera_id]: {
          emotion: data.emotion,
          confidence: data.confidence,
          timestamp: data.timestamp
        }
      }));
    };

    return () => ws.close();
  }, []);

  // Start processing a camera
  const startProcessing = async (cameraId) => {
    setLoadingStates(prev => ({ ...prev, [cameraId]: true }));
    try {
      await apiService.cameras.startCamera(cameraId);
      setActiveStates(prev => ({ ...prev, [cameraId]: true }));
    } catch (error) {
      setError('Không thể bật camera: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoadingStates(prev => ({ ...prev, [cameraId]: false }));
    }
  };

  // Stop processing a camera
  const stopProcessing = async (cameraId) => {
    setLoadingStates(prev => ({ ...prev, [cameraId]: true }));
    try {
      await apiService.cameras.stopCamera(cameraId);
      setActiveStates(prev => ({ ...prev, [cameraId]: false }));
    } catch (error) {
      setError('Không thể tắt camera: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoadingStates(prev => ({ ...prev, [cameraId]: false }));
    }
  };

  // Thêm hàm khởi tạo webcam
  const initializeWebcam = async (cameraId) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      const videoRef = videoRefs.current[cameraId];
      if (videoRef) {
        videoRef.srcObject = stream;
        setActiveCameras(prev => ({
          ...prev,
          [cameraId]: { ...prev[cameraId], active: true, error: null }
        }));
      }
    } catch (err) {
      console.error('Error accessing webcam:', err);
      setActiveCameras(prev => ({
        ...prev,
        [cameraId]: { ...prev[cameraId], error: 'Không thể truy cập webcam' }
      }));
    }
  };

  // Thêm hàm dừng webcam
  const stopWebcam = (cameraId) => {
    const videoRef = videoRefs.current[cameraId];
    if (videoRef && videoRef.srcObject) {
      const tracks = videoRef.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.srcObject = null;
      setActiveCameras(prev => ({
        ...prev,
        [cameraId]: { ...prev[cameraId], active: false }
      }));
    }
  };

  // Thêm hàm kết nối IP camera
  const connectIpCamera = async (cameraId, settings) => {
    try {
      setActiveCameras(prev => ({
        ...prev,
        [cameraId]: { ...prev[cameraId], loading: true, error: null }
      }));

      // Tạo URL stream trực tiếp từ cài đặt
      const streamUrl = `http://${settings.ipAddress}:${settings.port}${settings.path}`;
      
      // Kiểm tra kết nối bằng cách tạo một request tới URL stream
      const response = await fetch(streamUrl, { method: 'HEAD' });
      
      if (response.ok) {
        setActiveCameras(prev => ({
          ...prev,
          [cameraId]: { 
            ...prev[cameraId], 
            active: true, 
            loading: false,
            isIpCam: true,
            streamUrl: streamUrl
          }
        }));
      } else {
        throw new Error('Không thể kết nối IP camera');
      }
    } catch (err) {
      console.error('Error connecting IP camera:', err);
      setActiveCameras(prev => ({
        ...prev,
        [cameraId]: { 
          ...prev[cameraId], 
          active: false, 
          loading: false, 
          error: err.message || 'Không thể kết nối IP camera'
        }
      }));
    }
  };

  // Sửa hàm toggleCamera để xử lý IP camera
  const toggleCamera = async (camera) => {
    const cameraId = camera.id;
    const isActive = activeCameras[cameraId]?.active;
    const settings = cameraSettings[cameraId] || {};
    
    if (camera.camera_type === 'webcam') {
      if (isActive) {
        stopWebcam(cameraId);
      } else {
        initializeWebcam(cameraId);
      }
    } else if (camera.camera_type === 'ipcam') {
      if (isActive) {
        stopProcessing(cameraId);
      } else {
        await connectIpCamera(cameraId, settings);
      }
    } else {
      // Xử lý cho các loại camera khác
      if (isActive) {
        stopProcessing(cameraId);
      } else {
        startProcessing(cameraId);
      }
    }
  };

  // Handle refresh interval change
  const handleIntervalChange = (e) => {
    const newInterval = parseInt(e.target.value, 10);
    setRefreshInterval(newInterval);
  };

  // Toggle auto refresh
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  };

  // Handle grid layout change
  const handleGridChange = (e) => {
    setCameraGrid(e.target.value);
  };

  // Get column class based on grid setting
  const getColClass = () => {
    switch(cameraGrid) {
      case '1': return 12; // 1 camera per row
      case '2': return 6;  // 2 cameras per row
      case '3': return 4;  // 3 cameras per row
      case '4': return 3;  // 4 cameras per row
      default: return 4;   // Default 3 per row
    }
  };

  // Test camera connection
  const testCameraConnection = async (cameraId) => {
    try {
      const camera = cameras.find(c => c.id === cameraId);
      if (!camera) return;
      
      // Set status to connecting
      setCameras(prevCameras => prevCameras.map(c => 
        c.id === cameraId ? {...c, connection_status: 'connecting'} : c
      ));
      
      // Test connection
      const response = await apiService.cameras.testConnection(cameraId);
      
      // Update status based on response
      setCameras(prevCameras => prevCameras.map(c => 
        c.id === cameraId ? {
          ...c, 
          connection_status: response.data.success ? 'connected' : 'error',
          last_updated: new Date().toISOString()
        } : c
      ));
    } catch (err) {
      console.error(`Error testing camera ${cameraId}:`, err);
      
      // Set error status
      setCameras(prevCameras => prevCameras.map(c => 
        c.id === cameraId ? {...c, connection_status: 'error'} : c
      ));
    }
  };

  // Connect to camera
  const connectCamera = async (cameraId) => {
    try {
      const camera = cameras.find(c => c.id === cameraId);
      if (!camera) return;
      
      // Set status to connecting
      setCameras(prevCameras => prevCameras.map(c => 
        c.id === cameraId ? {...c, connection_status: 'connecting'} : c
      ));
      
      // Call connect API based on camera type
      let response;
      if (camera.camera_type === 'ipcam' || camera.camera_type === 'droidcam' || 
          camera.camera_type === 'rtsp' || camera.camera_type === 'mjpeg') {
        response = await apiService.cameras.connectIpCam(cameraId);
      } else {
        // Default for other types
        response = await apiService.cameras.testConnection(cameraId);
      }
      
      // Update camera data
      if (response.data.success || response.data.status === 'connected') {
        fetchCameras(); // Refresh all cameras
      } else {
        setCameras(prevCameras => prevCameras.map(c => 
          c.id === cameraId ? {
            ...c, 
            connection_status: 'error',
            last_updated: new Date().toISOString()
          } : c
        ));
      }
    } catch (err) {
      console.error(`Error connecting camera ${cameraId}:`, err);
      setCameras(prevCameras => prevCameras.map(c => 
        c.id === cameraId ? {...c, connection_status: 'error'} : c
      ));
    }
  };

  // Add function to render emotion overlay
  const renderEmotionOverlay = (cameraId) => {
    const result = emotionResults[cameraId];
    if (!result || !showEmotionOverlay) return null;

    return (
      <div className="emotion-overlay">
        <div className="emotion-label">
          <Badge bg="primary">{result.emotion}</Badge>
          <Badge bg="secondary">{Math.round(result.confidence * 100)}%</Badge>
        </div>
        <div className="timestamp">
          {formatDateTime(result.timestamp)}
        </div>
      </div>
    );
  };

  // Thêm hàm xử lý cài đặt
  const handleSettingsClick = (camera) => {
    setSelectedCamera(camera);
    setShowSettings(true);
  };

  const handleSaveSettings = (cameraId, settings) => {
    setCameraSettings(prev => ({
      ...prev,
      [cameraId]: settings
    }));
    
    // Gửi cài đặt mới lên backend
    apiService.cameras.updateSettings(cameraId, settings)
      .catch(err => console.error('Error updating settings:', err));
  };

  // Thêm hàm xử lý nhận diện khuôn mặt
  const handleFaceDetection = async (cameraId) => {
    try {
      setIsDetecting(prev => ({ ...prev, [cameraId]: true }));
      
      // Lấy cài đặt camera
      const settings = cameraSettings[cameraId] || {};
      const captureInterval = settings.captureInterval || 2; // Mặc định 2 giây
      
      // Tạo URL stream tùy theo loại camera
      let streamUrl;
      if (activeCameras[cameraId]?.isIpCam) {
        streamUrl = activeCameras[cameraId].streamUrl;
      } else {
        streamUrl = `http://localhost:5000/api/streams/${cameraId}?t=${Date.now()}`;
      }

      // Gọi API nhận diện khuôn mặt
      const response = await apiService.cameras.detectFaces(cameraId, {
        streamUrl,
        captureInterval,
        enableEmotionDetection: settings.enableEmotionDetection
      });

      if (response.data.success) {
        // Cập nhật trạng thái nhận diện
        setActiveCameras(prev => ({
          ...prev,
          [cameraId]: { 
            ...prev[cameraId], 
            isDetecting: true,
            lastDetection: new Date().toISOString()
          }
        }));
      } else {
        throw new Error(response.data.message || 'Không thể bắt đầu nhận diện');
      }
    } catch (err) {
      console.error('Error starting face detection:', err);
      setActiveCameras(prev => ({
        ...prev,
        [cameraId]: { 
          ...prev[cameraId], 
          error: err.message || 'Không thể bắt đầu nhận diện'
        }
      }));
    } finally {
      setIsDetecting(prev => ({ ...prev, [cameraId]: false }));
    }
  };

  // Sửa hàm renderCameraFeed để thêm nút nhận diện
  const renderCameraFeed = (camera) => {
    const cameraId = camera.id;
    const isActive = activeCameras[cameraId]?.active;
    const error = activeCameras[cameraId]?.error;
    const isLoading = activeCameras[cameraId]?.loading;
    const isIpCam = activeCameras[cameraId]?.isIpCam;
    const streamUrl = activeCameras[cameraId]?.streamUrl;
    const isDetectingFaces = activeCameras[cameraId]?.isDetecting;

    return (
      <Col key={cameraId} xs={12} md={getColClass()} className="camera-column">
        <CameraPlaceholder
          camera={camera}
          isActive={activeStates[cameraId]}
          onStart={startProcessing}
          onStop={stopProcessing}
          loading={loadingStates[cameraId]}
        />
      </Col>
    );
  };

  return (
    <Container fluid className="my-3">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Xem nhiều camera</h2>
      </div>
      
      {/* Controls */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 bg-light p-3 rounded">
        <div className="d-flex flex-wrap align-items-center">
          <Button 
            variant={autoRefresh ? "success" : "outline-secondary"} 
            onClick={toggleAutoRefresh} 
            className="me-2 mb-2"
          >
            <i className="bi bi-arrow-repeat me-1"></i>
            {autoRefresh ? "Tự động làm mới: Bật" : "Tự động làm mới: Tắt"}
          </Button>
          
          <Form.Select 
            value={refreshInterval} 
            onChange={handleIntervalChange} 
            style={{ width: 'auto' }}
            disabled={!autoRefresh}
            className="me-2 mb-2"
          >
            <option value={1000}>Làm mới: 1s</option>
            <option value={3000}>Làm mới: 3s</option>
            <option value={5000}>Làm mới: 5s</option>
            <option value={10000}>Làm mới: 10s</option>
          </Form.Select>
          
          <Button 
            variant="primary" 
            onClick={fetchCameras} 
            className="me-2 mb-2"
            disabled={loading}
          >
            {loading ? (
              <>
                <Spinner
                  as="span"
                  animation="border"
                  size="sm"
                  role="status"
                  aria-hidden="true"
                  className="me-1"
                />
                Đang làm mới...
              </>
            ) : (
              <>
                <i className="bi bi-arrow-clockwise me-1"></i>
                Làm mới ngay
              </>
            )}
          </Button>
          
          <Form.Select
            value={cameraGrid}
            onChange={handleGridChange}
            style={{ width: 'auto' }}
            className="mb-2"
          >
            <option value="1">Hiển thị 1 camera/hàng</option>
            <option value="2">Hiển thị 2 camera/hàng</option>
            <option value="3">Hiển thị 3 camera/hàng</option>
            <option value="4">Hiển thị 4 camera/hàng</option>
          </Form.Select>
        </div>
        
        <div className="text-muted mb-2">
          Đang hiển thị {cameras.length} camera{cameras.length !== 1 ? 's' : ''}
        </div>
      </div>
      
      {/* Loading and error states */}
      {loading && cameras.length === 0 && (
        <div className="text-center my-5">
          <Spinner animation="border" role="status" />
          <p className="mt-2">Đang tải dữ liệu camera...</p>
        </div>
      )}
      
      {error && <Alert variant="danger">{error}</Alert>}
      
      {/* Hiển thị nút "Kết nối tất cả camera" nếu có camera chưa kết nối */}
      {cameras.length > 0 && cameras.some(c => c.connection_status !== 'connected') && (
        <div className="mb-3">
          <Button 
            variant="success"
            onClick={() => {
              cameras.forEach(camera => {
                if (camera.connection_status !== 'connected') {
                  connectCamera(camera.id);
                }
              });
            }}
          >
            <i className="bi bi-broadcast me-1"></i>
            Kết nối tất cả camera
          </Button>
        </div>
      )}
      
      {/* Camera grid */}
      {!loading && !error && (
        cameras.length > 0 ? (
          <Row xs={1} md={getColClass()} className="g-3">
            {cameras.map(renderCameraFeed)}
          </Row>
        ) : (
          <Alert variant="info">
            <Alert.Heading>Không có camera nào đang hoạt động</Alert.Heading>
            <p>Vui lòng kích hoạt ít nhất một camera từ mục Quản lý Camera.</p>
            <div className="d-grid gap-2 d-md-flex justify-content-md-end">
              <Button 
                variant="primary"
                onClick={() => document.querySelector('a[data-rr-ui-event-key="manage"]').click()}
              >
                Đến Quản lý Camera
              </Button>
            </div>
          </Alert>
        )
      )}
      
      {/* Thêm modal cài đặt */}
      {selectedCamera && (
        <CameraSettings
          show={showSettings}
          onHide={() => setShowSettings(false)}
          camera={selectedCamera}
          onSave={handleSaveSettings}
        />
      )}
    </Container>
  );
};

export default MultipleCameraView; 
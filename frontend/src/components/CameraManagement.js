import React, { useState, useEffect } from 'react';
import { Container, Button, Table, Modal, Form, Row, Col, Alert, Spinner, Badge } from 'react-bootstrap';
import apiService from '../services/api';

const CameraManagement = () => {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  const [selectedCameraId, setSelectedCameraId] = useState(null);
  const [scheduleType, setScheduleType] = useState('interval');
  const [intervalMinutes, setIntervalMinutes] = useState(15);
  const [scheduleHour, setScheduleHour] = useState('*');
  const [scheduleMinute, setScheduleMinute] = useState('0');
  const [schedules, setSchedules] = useState([]);
  const [captureLoading, setCaptureLoading] = useState(false);
  const [connectedCameras, setConnectedCameras] = useState({});
  const [showNoCameraMessage, setShowNoCameraMessage] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [cameraStates, setCameraStates] = useState({});

  const [formData, setFormData] = useState({
    name: '',
    camera_type: 'webcam',
    location: '',
    ip_address: '',
    port: '',
    status: 'active',
    connection_status: 'disconnected'
  });

  useEffect(() => {
    fetchCameras();
    loadSchedules();
    fetchCameraStates();
  }, []);

  useEffect(() => {
    // Thêm chức năng hiển thị nút tạo camera mặc định khi không có camera nào
    if (cameras && cameras.length === 0 && !loading && !error) {
      setShowNoCameraMessage(true);
    } else {
      setShowNoCameraMessage(false);
    }
  }, [cameras, loading, error]);

  useEffect(() => {
    // Ẩn thông báo thành công sau 3 giây
    if (success) {
      const timer = setTimeout(() => {
        setSuccess(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  const fetchCameras = async () => {
    try {
      setLoading(true);
      const response = await apiService.cameras.getAll();
      
      // Kiểm tra và xử lý dữ liệu từ API
      if (response && response.data) {
        // Nếu dữ liệu là mảng, sử dụng trực tiếp
        if (Array.isArray(response.data)) {
          setCameras(response.data);
        } 
        // Nếu dữ liệu có thuộc tính cameras hoặc camera, sử dụng nó
        else if (response.data.cameras) {
          setCameras(response.data.cameras);
        }
        else if (response.data.camera) {
          setCameras(response.data.camera);
        }
        // Trường hợp không có dữ liệu như mong đợi
        else {
          console.warn("Dữ liệu trả về không đúng định dạng:", response.data);
          setCameras([]);
        }
      } else {
        // Không có dữ liệu, hiển thị mảng rỗng
        setCameras([]);
      }
    } catch (error) {
      console.error("Error fetching cameras:", error);
      setError('Không thể tải danh sách camera');
      setCameras([]); // Đặt cameras thành mảng rỗng khi có lỗi
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const resetForm = () => {
    setFormData({
      name: '',
      camera_type: 'webcam',
      location: '',
      ip_address: '',
      port: '',
      status: 'active',
      connection_status: 'disconnected'
    });
    setEditingCamera(null);
    setError('');
  };

  const handleAddNew = () => {
    resetForm();
    setShowModal(true);
  };

  const handleEdit = (camera) => {
    setEditingCamera(camera);
    setFormData({
      name: camera.name,
      camera_type: camera.camera_type,
      location: camera.location || '',
      ip_address: camera.ip_address || '',
      port: camera.port || '',
      status: camera.status || 'active',
      connection_status: camera.connection_status || 'disconnected'
    });
    setShowModal(true);
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      setError('Vui lòng nhập tên camera');
      return false;
    }

    if (formData.camera_type === 'ipcam') {
      if (!formData.ip_address) {
        setError('Vui lòng nhập địa chỉ IP');
        return false;
      }
      if (!formData.port) {
        setError('Vui lòng nhập port');
        return false;
      }
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const cameraData = {
        ...formData,
        port: formData.port ? parseInt(formData.port) : null
      };

      if (formData.camera_type === 'ipcam') {
        cameraData.stream_url = `http://${formData.ip_address}:${formData.port}/video`;
      }

      if (editingCamera) {
        await apiService.cameras.update(editingCamera.id, cameraData);
        setSuccess('Camera đã được cập nhật thành công');
      } else {
        await apiService.cameras.add(cameraData);
        setSuccess('Camera đã được thêm thành công');
      }

      fetchCameras();
      setShowModal(false);
      resetForm();
    } catch (err) {
      setError(err.response?.data?.message || 'Có lỗi xảy ra');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (camera) => {
    if (window.confirm(`Bạn có chắc muốn xóa camera "${camera.name}"?`)) {
      try {
        await apiService.cameras.delete(camera.id);
        setSuccess('Camera đã được xóa thành công');
        fetchCameras();
      } catch (err) {
        setError('Không thể xóa camera');
      }
    }
  };

  const testConnection = async (camera) => {
    setTestingConnection(true);
    setTestResult(null);
    
    try {
      let testData = {
        type: camera.camera_type
      };
      
      // Add fields based on camera type
      if (['droidcam', 'ipcam', 'rtsp', 'mjpeg'].includes(camera.camera_type)) {
        testData.ip_address = camera.ip_address;
        testData.port = parseInt(camera.port);
        
        if (camera.camera_type === 'rtsp') {
          testData.username = camera.username;
          testData.password = camera.password;
          testData.stream_path = camera.stream_path;
        } else if (camera.camera_type === 'mjpeg') {
          testData.stream_path = camera.stream_path;
        }
      } else if (camera.camera_type === 'public_url') {
        testData.stream_url = camera.stream_url;
      }
      
      // If editing an existing camera, use the test endpoint for that camera
      let response;
      if (editingCamera) {
        response = await apiService.cameras.testConnection(editingCamera.id);
      } else {
        response = await apiService.cameras.test(testData);
      }
      
      setTestResult({
        success: response.data.connection_status === 'connected',
        message: response.data.message,
        details: response.data
      });
    } catch (err) {
      setTestResult({
        success: false,
        message: 'Kết nối thất bại',
        details: err.response?.data || { error: err.message }
      });
      console.error('Test connection error:', err);
    } finally {
      setTestingConnection(false);
    }
  };

  const formatDateTime = (timestamp) => {
    if (!timestamp) return 'Chưa kết nối';
    const date = new Date(timestamp);
    return date.toLocaleString('vi-VN');
  };

  const renderConnectionBadge = (camera) => {
    if (!camera.connection_status || camera.connection_status === 'disconnected') {
      return <Badge bg="secondary">Không kết nối</Badge>;
    } else if (camera.connection_status === 'connected') {
      return <Badge bg="success">Đã kết nối</Badge>;
    } else {
      return <Badge bg="danger">Lỗi kết nối</Badge>;
    }
  };

  const renderTestResult = () => {
    if (!testResult) return null;
    
    return (
      <Alert variant={testResult.success ? 'success' : 'danger'} className="mt-3">
        <Alert.Heading>{testResult.success ? 'Kết nối thành công!' : 'Kết nối thất bại!'}</Alert.Heading>
        <p>{testResult.message}</p>
        {testResult.details && (
          <pre className="small mt-2" style={{ whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(testResult.details, null, 2)}
          </pre>
        )}
      </Alert>
    );
  };

  const renderCameraTypeFields = () => {
    switch (cameraType) {
      case 'webcam':
        return (
          <Alert variant="info">
            Sử dụng webcam của máy tính. Không cần thêm thông tin.
          </Alert>
        );
      
      case 'droidcam':
      case 'ipcam':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Địa chỉ IP</Form.Label>
              <Form.Control
                type="text"
                value={ipAddress}
                onChange={(e) => setIpAddress(e.target.value)}
                placeholder="VD: 192.168.1.100"
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Port</Form.Label>
              <Form.Control
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder={cameraType === 'droidcam' ? "4747" : "554"}
                required
              />
              {cameraType === 'droidcam' && (
                <Form.Text className="text-muted">
                  Port mặc định của DroidCam là 4747
                </Form.Text>
              )}
            </Form.Group>
          </>
        );
      
      case 'rtsp':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Địa chỉ IP</Form.Label>
              <Form.Control
                type="text"
                value={ipAddress}
                onChange={(e) => setIpAddress(e.target.value)}
                placeholder="VD: 192.168.1.100"
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Port</Form.Label>
              <Form.Control
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="554"
                required
              />
              <Form.Text className="text-muted">
                Port mặc định của camera RTSP là 554
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Tên đăng nhập (nếu có)</Form.Label>
              <Form.Control
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Tên đăng nhập"
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Mật khẩu (nếu có)</Form.Label>
              <Form.Control
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mật khẩu"
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Đường dẫn stream</Form.Label>
              <Form.Control
                type="text"
                value={streamPath}
                onChange={(e) => setStreamPath(e.target.value)}
                placeholder="VD: live/stream1"
                required
              />
              <Form.Text className="text-muted">
                Đường dẫn stream phụ thuộc vào model camera của bạn
              </Form.Text>
            </Form.Group>
          </>
        );
      
      case 'mjpeg':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>Địa chỉ IP</Form.Label>
              <Form.Control
                type="text"
                value={ipAddress}
                onChange={(e) => setIpAddress(e.target.value)}
                placeholder="VD: 192.168.1.100"
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Port</Form.Label>
              <Form.Control
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="80"
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Đường dẫn stream</Form.Label>
              <Form.Control
                type="text"
                value={streamPath}
                onChange={(e) => setStreamPath(e.target.value)}
                placeholder="VD: video"
                required
              />
            </Form.Group>
          </>
        );
      
      case 'public_url':
        return (
          <>
            <Form.Group className="mb-3">
              <Form.Label>URL Stream Public</Form.Label>
              <Form.Control
                type="text"
                value={streamUrl}
                onChange={(e) => setStreamUrl(e.target.value)}
                placeholder="VD: https://xxxxx.ngrok.io/video"
                required
              />
              <Form.Text className="text-muted">
                URL công khai đến nguồn video (VD: URL từ ngrok, cloudflare tunnel, ...)
              </Form.Text>
            </Form.Group>
          </>
        );
      
      default:
        return null;
    }
  };

  // Load camera schedules
  const loadSchedules = async () => {
    try {
      const response = await apiService.schedules.getAll();
      if (response && response.data) {
        setSchedules(response.data);
      } else {
        setSchedules([]);
      }
    } catch (error) {
      console.error('Error loading schedules:', error);
      setError('Không thể tải lịch trình camera');
      setSchedules([]);
    }
  };

  // Hàm xử lý chụp ảnh từ camera RTSP
  const handleCaptureRtsp = async (cameraId) => {
    setCaptureLoading(true);
    setSelectedCameraId(cameraId);
    
    try {
      const response = await apiService.cameras.captureRtsp(cameraId);
      setSuccess(`Đã chụp và xử lý ảnh thành công từ camera ID ${cameraId}. Cảm xúc: ${response.data.dominant_emotion}`);
    } catch (error) {
      console.error('Error capturing RTSP image:', error);
      setError(error.response?.data?.error || 'Không thể chụp ảnh từ camera RTSP');
    } finally {
      setCaptureLoading(false);
    }
  };

  // Mở modal lên lịch camera
  const openScheduleModal = (cameraId) => {
    setSelectedCameraId(cameraId);
    setShowScheduleModal(true);
    
    // Kiểm tra xem camera này đã có lịch chưa
    const existingSchedule = schedules.find(s => s.camera_id === cameraId);
    if (existingSchedule) {
      setScheduleType(existingSchedule.type);
      if (existingSchedule.type === 'interval') {
        setIntervalMinutes(existingSchedule.interval_minutes);
      } else {
        setScheduleHour(existingSchedule.hour);
        setScheduleMinute(existingSchedule.minute);
      }
    } else {
      // Reset về giá trị mặc định
      setScheduleType('interval');
      setIntervalMinutes(15);
      setScheduleHour('*');
      setScheduleMinute('0');
    }
  };

  // Xử lý lưu lịch trình
  const handleSaveSchedule = async () => {
    try {
      const scheduleData = {
        camera_id: selectedCameraId,
        schedule_type: scheduleType
      };
      
      if (scheduleType === 'interval') {
        scheduleData.interval_minutes = parseInt(intervalMinutes);
      } else {
        scheduleData.hour = scheduleHour;
        scheduleData.minute = scheduleMinute;
      }
      
      await apiService.schedules.create(scheduleData);
      
      setShowScheduleModal(false);
      setSuccess('Lịch trình đã được lưu thành công');
      loadSchedules();
      
      // Tự động ẩn thông báo thành công sau 3 giây
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (error) {
      setError('Không thể lưu lịch trình: ' + (error.response?.data?.error || error.message));
      console.error("Error saving schedule:", error);
    }
  };

  // Xử lý xóa lịch trình
  const handleDeleteSchedule = async (cameraId) => {
    if (window.confirm('Bạn có chắc muốn xóa lịch trình cho camera này?')) {
      try {
        await apiService.schedules.delete(cameraId);
        loadSchedules();
        setSuccess('Lịch trình đã được xóa thành công');
        
        // Tự động ẩn thông báo thành công sau 3 giây
        setTimeout(() => {
          setSuccess(null);
        }, 3000);
      } catch (error) {
        setError('Không thể xóa lịch trình: ' + (error.response?.data?.error || error.message));
        console.error("Error deleting schedule:", error);
      }
    }
  };

  // Hàm kết nối với IP Camera để xử lý video
  const handleConnectIpCam = async (cameraId) => {
    try {
      setConnectedCameras({
        ...connectedCameras,
        [cameraId]: {
          isConnecting: true,
          isConnected: false
        }
      });
      
      const response = await apiService.cameras.connectIpCam(cameraId);
      
      setConnectedCameras({
        ...connectedCameras,
        [cameraId]: {
          isConnecting: false,
          isConnected: true
        }
      });
      
      setSuccess(`Camera ${cameraId} đã kết nối thành công`);
      fetchCameras();
      
      // Tự động ẩn thông báo thành công sau 3 giây
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (error) {
      setConnectedCameras({
        ...connectedCameras,
        [cameraId]: {
          isConnecting: false,
          isConnected: false,
          error: true
        }
      });
      
      setError('Không thể kết nối camera: ' + (error.response?.data?.error || error.message));
      console.error("Error connecting camera:", error);
    }
  };

  // Hàm ngắt kết nối với camera
  const handleDisconnectCamera = async (cameraId) => {
    try {
      await apiService.cameras.disconnect(cameraId);
      
      setConnectedCameras({
        ...connectedCameras,
        [cameraId]: {
          isConnecting: false,
          isConnected: false
        }
      });
      
      setSuccess(`Camera ${cameraId} đã ngắt kết nối thành công`);
      fetchCameras();
      
      // Tự động ẩn thông báo thành công sau 3 giây
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (error) {
      setError('Không thể ngắt kết nối camera: ' + (error.response?.data?.error || error.message));
      console.error("Error disconnecting camera:", error);
    }
  };

  // Hàm render nút kết nối/ngắt kết nối camera
  const renderConnectionButton = (camera) => {
    const connectionStatus = connectedCameras[camera.id];
    
    if (connectionStatus === 'connected') {
      return (
        <Button
          variant="danger"
          size="sm"
          className="me-1"
          onClick={() => handleDisconnectCamera(camera.id)}
        >
          Ngắt kết nối
        </Button>
      );
    }
    
    if (connectionStatus === 'connecting') {
      return (
        <Button
          variant="secondary"
          size="sm"
          className="me-1"
          disabled
        >
          <Spinner
            as="span"
            animation="border"
            size="sm"
            role="status"
            aria-hidden="true"
          />
          <span className="ms-1">Đang kết nối...</span>
        </Button>
      );
    }
    
    if (camera.camera_type === 'ipcam' || camera.camera_type === 'droidcam') {
      return (
        <Button
          variant="success"
          size="sm"
          className="me-1"
          onClick={() => handleConnectIpCam(camera.id)}
        >
          Kết nối trực tiếp
        </Button>
      );
    }
    
    return null;
  };

  const createDefaultCameras = async () => {
    try {
      setLoading(true);
      // Tạo camera mặc định - webcam
      await apiService.cameras.add({
        name: "Default Webcam",
        location: "Local",
        type: "webcam",
        status: "active"
      });
      
      // Tải lại danh sách camera
      await fetchCameras();
      setShowNoCameraMessage(false);
    } catch (err) {
      console.error("Error creating default camera:", err);
      setError("Không thể tạo camera mặc định. Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (camera) => {
    try {
      const newStatus = camera.status === 'active' ? 'inactive' : 'active';
      await apiService.cameras.update(camera.id, {
        ...camera,
        status: newStatus
      });
      setSuccess(`Đã ${newStatus === 'active' ? 'bật' : 'tắt'} camera ${camera.name}`);
      fetchCameras();
    } catch (err) {
      setError('Không thể thay đổi trạng thái camera');
    }
  };

  // Hàm để lấy trạng thái của tất cả camera
  const fetchCameraStates = async () => {
    try {
      const cameras = await apiService.cameras.getAll();
      const states = {};
      
      for (const camera of cameras.data) {
        try {
          const statusResponse = await apiService.cameras.getStatus(camera.id);
          states[camera.id] = statusResponse.data.is_active;
        } catch (error) {
          console.error(`Error getting status for camera ${camera.id}:`, error);
          states[camera.id] = false;
        }
      }
      
      setCameraStates(states);
    } catch (error) {
      console.error('Error fetching camera states:', error);
    }
  };

  // Hàm xử lý bật camera
  const handleStartCamera = async (cameraId) => {
    try {
      setLoading(true);
      await apiService.cameras.startCamera(cameraId);
      setCameraStates(prev => ({
        ...prev,
        [cameraId]: true
      }));
      setSuccess('Camera đã được bật thành công');
    } catch (error) {
      setError('Không thể bật camera. ' + (error.response?.data?.message || ''));
    } finally {
      setLoading(false);
    }
  };

  // Hàm xử lý tắt camera
  const handleStopCamera = async (cameraId) => {
    try {
      setLoading(true);
      await apiService.cameras.stopCamera(cameraId);
      setCameraStates(prev => ({
        ...prev,
        [cameraId]: false
      }));
      setSuccess('Camera đã được tắt thành công');
    } catch (error) {
      setError('Không thể tắt camera. ' + (error.response?.data?.message || ''));
    } finally {
      setLoading(false);
    }
  };

  // Hàm render nút điều khiển camera
  const renderCameraControls = (camera) => {
    const isActive = cameraStates[camera.id];
    
    return (
      <>
        <Button
          variant={isActive ? "danger" : "success"}
          size="sm"
          className="me-1"
          onClick={() => isActive ? handleStopCamera(camera.id) : handleStartCamera(camera.id)}
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
              Đang xử lý...
            </>
          ) : (
            isActive ? 'Tắt Camera' : 'Bật Camera'
          )}
        </Button>
      </>
    );
  };

  return (
    <Container fluid className="py-3">
      <Row className="mb-3">
        <Col>
          <h2>Quản lý Camera</h2>
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleAddNew} className="me-2">
            <i className="bi bi-plus-circle me-1"></i> Thêm Camera mới
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}
      
      {showNoCameraMessage && !loading && (
        <Alert variant="info">
          <Alert.Heading>Chưa có camera nào trong hệ thống</Alert.Heading>
          <p>Bạn chưa cài đặt camera nào. Hãy thêm camera mới hoặc tạo camera mặc định để bắt đầu.</p>
          <div className="d-flex justify-content-end">
            <Button variant="outline-primary" onClick={createDefaultCameras}>
              <i className="bi bi-camera me-1"></i> Tạo Camera mặc định
            </Button>
          </div>
        </Alert>
      )}

      {loading ? (
        <div className="text-center my-5">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Đang tải...</span>
          </Spinner>
        </div>
      ) : (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Vị trí</th>
              <th>Loại</th>
              <th>Trạng thái</th>
              <th>Kết nối</th>
              <th>Kết nối cuối</th>
              <th>Lịch trình</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {cameras.length === 0 ? (
              <tr>
                <td colSpan="9" className="text-center">
                  Không có camera nào. Hãy thêm camera mới.
                </td>
              </tr>
            ) : (
              cameras.map((camera) => {
                const schedule = schedules.find(s => s.camera_id === camera.id);
                return (
                <tr key={camera.id}>
                  <td>{camera.id}</td>
                  <td>{camera.name}</td>
                  <td>{camera.location || '-'}</td>
                  <td>{camera.camera_type}</td>
                  <td>
                    <Badge bg={cameraStates[camera.id] ? 'success' : 'danger'}>
                      {cameraStates[camera.id] ? 'Đang hoạt động' : 'Đã tắt'}
                    </Badge>
                  </td>
                  <td>{renderConnectionBadge(camera)}</td>
                  <td>{formatDateTime(camera.last_connected)}</td>
                  <td>
                    {schedule ? (
                      <div>
                        {schedule.type === 'interval' ? (
                          <Badge bg="info">Mỗi {schedule.interval_minutes} phút</Badge>
                        ) : (
                          <Badge bg="info">
                            {schedule.hour === '*' ? 'Hàng giờ' : `${schedule.hour}:${schedule.minute}`}
                          </Badge>
                        )}
                        <Button
                          variant="danger"
                          size="sm"
                          className="ms-1"
                          onClick={() => handleDeleteSchedule(camera.id)}
                        >
                          Xóa
                        </Button>
                      </div>
                    ) : (
                      <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={() => openScheduleModal(camera.id)}
                      >
                        Đặt lịch
                      </Button>
                    )}
                  </td>
                  <td>
                    {renderCameraControls(camera)}
                    <Button
                      variant="info"
                      size="sm"
                      className="me-1"
                      onClick={() => handleEdit(camera)}
                    >
                      Sửa
                    </Button>
                    {renderConnectionButton(camera)}
                    {camera.camera_type === 'rtsp' && (
                      <Button
                        variant="primary"
                        size="sm"
                        className="me-1"
                        onClick={() => handleCaptureRtsp(camera.id)}
                        disabled={captureLoading && selectedCameraId === camera.id}
                      >
                        {captureLoading && selectedCameraId === camera.id ? (
                          <>
                            <Spinner 
                              as="span" 
                              animation="border" 
                              size="sm" 
                              role="status" 
                              aria-hidden="true"
                            />
                            <span className="ms-1">Đang chụp...</span>
                          </>
                        ) : (
                          'Chụp ảnh'
                        )}
                      </Button>
                    )}
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDelete(camera)}
                    >
                      Xóa
                    </Button>
                  </td>
                </tr>
              )})
            )}
          </tbody>
        </Table>
      )}

      {/* Modal for adding/editing camera */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{editingCamera ? 'Chỉnh sửa Camera' : 'Thêm Camera Mới'}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Tên Camera</Form.Label>
              <Form.Control
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Nhập tên camera"
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Vị trí</Form.Label>
              <Form.Control
                type="text"
                name="location"
                value={formData.location}
                onChange={handleInputChange}
                placeholder="Nhập vị trí đặt camera"
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Loại Camera</Form.Label>
              <Form.Select
                name="camera_type"
                value={formData.camera_type}
                onChange={handleInputChange}
              >
                <option value="webcam">Webcam</option>
                <option value="ipcam">IP Camera</option>
              </Form.Select>
            </Form.Group>

            {formData.camera_type === 'ipcam' && (
              <>
                <Form.Group className="mb-3">
                  <Form.Label>Địa chỉ IP</Form.Label>
                  <Form.Control
                    type="text"
                    name="ip_address"
                    value={formData.ip_address}
                    onChange={handleInputChange}
                    placeholder="Ví dụ: 192.168.1.100"
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>Port</Form.Label>
                  <Form.Control
                    type="text"
                    name="port"
                    value={formData.port}
                    onChange={handleInputChange}
                    placeholder="Ví dụ: 8080"
                  />
                </Form.Group>
              </>
            )}

            <Form.Group className="mb-3">
              <Form.Label>Trạng thái</Form.Label>
              <Form.Select
                name="status"
                value={formData.status}
                onChange={handleInputChange}
              >
                <option value="active">Hoạt động</option>
                <option value="inactive">Không hoạt động</option>
              </Form.Select>
            </Form.Group>

            <div className="d-flex justify-content-between">
              <Button variant="secondary" onClick={() => setShowModal(false)}>
                Hủy
              </Button>
              <Button
                variant="primary"
                type="submit"
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
                    />
                    <span className="ms-1">Đang thêm...</span>
                  </>
                ) : (
                  'Thêm Camera'
                )}
              </Button>
            </div>
          </Form>
        </Modal.Body>
      </Modal>

      {/* Modal for schedule management */}
      <Modal show={showScheduleModal} onHide={() => setShowScheduleModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Thiết lập lịch trình chụp ảnh</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Loại lịch trình</Form.Label>
              <Form.Select 
                value={scheduleType}
                onChange={(e) => setScheduleType(e.target.value)}
              >
                <option value="interval">Định kỳ theo khoảng thời gian</option>
                <option value="fixed">Thời điểm cố định</option>
              </Form.Select>
            </Form.Group>

            {scheduleType === 'interval' ? (
              <Form.Group className="mb-3">
                <Form.Label>Chụp mỗi (phút)</Form.Label>
                <Form.Control
                  type="number"
                  min="1"
                  max="1440"
                  value={intervalMinutes}
                  onChange={(e) => setIntervalMinutes(e.target.value)}
                />
                <Form.Text className="text-muted">
                  Khoảng thời gian giữa các lần chụp (từ 1 đến 1440 phút)
                </Form.Text>
              </Form.Group>
            ) : (
              <>
                <Row>
                  <Col>
                    <Form.Group className="mb-3">
                      <Form.Label>Giờ</Form.Label>
                      <Form.Select 
                        value={scheduleHour}
                        onChange={(e) => setScheduleHour(e.target.value)}
                      >
                        <option value="*">Mỗi giờ</option>
                        {[...Array(24).keys()].map(hour => (
                          <option key={hour} value={hour}>{hour}</option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col>
                    <Form.Group className="mb-3">
                      <Form.Label>Phút</Form.Label>
                      <Form.Select 
                        value={scheduleMinute}
                        onChange={(e) => setScheduleMinute(e.target.value)}
                        disabled={scheduleHour === '*'}
                      >
                        {[...Array(60).keys()].map(minute => (
                          <option key={minute} value={minute}>{minute}</option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>
                <Form.Text className="text-muted">
                  Chọn "Mỗi giờ" để chụp hàng giờ vào phút thứ 0
                </Form.Text>
              </>
            )}
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowScheduleModal(false)}>
            Hủy bỏ
          </Button>
          <Button variant="primary" onClick={handleSaveSchedule}>
            Lưu lịch trình
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default CameraManagement; 
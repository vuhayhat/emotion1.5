import React, { useState, useEffect } from 'react';
import { Container, Table, Button, Modal, Form, Alert, Spinner, Badge } from 'react-bootstrap';
import axios from 'axios';

const API_URL = 'http://localhost:5000';

const CameraManagement = () => {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  const [cameraName, setCameraName] = useState('');
  const [cameraLocation, setCameraLocation] = useState('');
  const [cameraType, setCameraType] = useState('webcam');
  const [ipAddress, setIpAddress] = useState('');
  const [port, setPort] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [streamPath, setStreamPath] = useState('');
  const [streamUrl, setStreamUrl] = useState('');
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState(null);
  
  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/api/cameras`);
      setCameras(response.data);
    } catch (err) {
      setError('Không thể tải danh sách camera. Vui lòng thử lại sau.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddNew = () => {
    setEditingCamera(null);
    setCameraName('');
    setCameraLocation('');
    setCameraType('webcam');
    setIpAddress('');
    setPort('');
    setUsername('');
    setPassword('');
    setStreamPath('');
    setStreamUrl('');
    setTestResult(null);
    setShowModal(true);
  };

  const handleEdit = (camera) => {
    setEditingCamera(camera);
    setCameraName(camera.name);
    setCameraLocation(camera.location || '');
    setCameraType(camera.camera_type);
    setIpAddress(camera.ip_address || '');
    setPort(camera.port || '');
    setUsername(camera.username || '');
    setPassword(''); // Don't set password for security reasons
    setStreamPath(camera.stream_path || '');
    setStreamUrl(camera.stream_url || '');
    setTestResult(null);
    setShowModal(true);
  };

  const testConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);
    
    try {
      let testData = {
        type: cameraType
      };
      
      // Add fields based on camera type
      if (['droidcam', 'ipcam', 'rtsp', 'mjpeg'].includes(cameraType)) {
        testData.ip_address = ipAddress;
        testData.port = parseInt(port);
        
        if (cameraType === 'rtsp') {
          testData.username = username;
          testData.password = password;
          testData.stream_path = streamPath;
        } else if (cameraType === 'mjpeg') {
          testData.stream_path = streamPath;
        }
      } else if (cameraType === 'public_url') {
        testData.stream_url = streamUrl;
      }
      
      // If editing an existing camera, use the test endpoint for that camera
      let response;
      if (editingCamera) {
        response = await axios.post(`${API_URL}/api/cameras/${editingCamera.id}/test`, {});
      } else {
        response = await axios.post(`${API_URL}/api/cameras/test`, testData);
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

  const validateForm = () => {
    if (!cameraName.trim()) {
      setError('Tên camera không được để trống');
      return false;
    }
    
    if (['droidcam', 'ipcam', 'rtsp', 'mjpeg'].includes(cameraType)) {
      if (!ipAddress.trim()) {
        setError('Địa chỉ IP không được để trống');
        return false;
      }
      
      if (!port || isNaN(parseInt(port))) {
        setError('Port phải là một số hợp lệ');
        return false;
      }
      
      if (cameraType === 'rtsp' && !streamPath.trim()) {
        setError('Đường dẫn stream không được để trống');
        return false;
      }
    } else if (cameraType === 'public_url') {
      if (!streamUrl.trim()) {
        setError('URL stream không được để trống');
        return false;
      }
      
      try {
        new URL(streamUrl);
      } catch (e) {
        setError('URL stream không hợp lệ');
        return false;
      }
    }
    
    return true;
  };

  const handleSave = async () => {
    if (!validateForm()) return;
    
    setLoading(true);
    setError(null);
    
    const cameraData = {
      name: cameraName,
      location: cameraLocation,
      type: cameraType
    };
    
    // Add fields based on camera type
    if (['droidcam', 'ipcam', 'rtsp', 'mjpeg'].includes(cameraType)) {
      cameraData.ip_address = ipAddress;
      cameraData.port = parseInt(port);
      
      if (cameraType === 'rtsp') {
        cameraData.username = username;
        cameraData.password = password;
        cameraData.stream_path = streamPath;
      } else if (cameraType === 'mjpeg') {
        cameraData.stream_path = streamPath;
      }
    } else if (cameraType === 'public_url') {
      cameraData.stream_url = streamUrl;
    }
    
    try {
      if (editingCamera) {
        await axios.put(`${API_URL}/api/cameras/${editingCamera.id}`, cameraData);
      } else {
        await axios.post(`${API_URL}/api/cameras`, cameraData);
      }
      
      setShowModal(false);
      fetchCameras();
    } catch (err) {
      setError('Không thể lưu camera. Vui lòng thử lại sau.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (camera) => {
    try {
      await axios.put(`${API_URL}/api/cameras/${camera.id}/status`, {
        status: camera.status === 'active' ? 'inactive' : 'active'
      });
      fetchCameras();
    } catch (err) {
      setError('Không thể cập nhật trạng thái camera.');
      console.error(err);
    }
  };

  const handleDelete = async (camera) => {
    if (window.confirm(`Bạn có chắc muốn xóa camera "${camera.name}"?`)) {
      try {
        await axios.delete(`${API_URL}/api/cameras/${camera.id}`);
        fetchCameras();
      } catch (err) {
        setError('Không thể xóa camera.');
        console.error(err);
      }
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

  return (
    <Container>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Quản lý Camera</h2>
        <Button variant="primary" onClick={handleAddNew}>
          Thêm Camera
        </Button>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      {loading && !showModal ? (
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
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {cameras.length === 0 ? (
              <tr>
                <td colSpan="8" className="text-center">
                  Không có camera nào. Hãy thêm camera mới.
                </td>
              </tr>
            ) : (
              cameras.map((camera) => (
                <tr key={camera.id}>
                  <td>{camera.id}</td>
                  <td>{camera.name}</td>
                  <td>{camera.location || '-'}</td>
                  <td>{camera.camera_type}</td>
                  <td>
                    <Badge bg={camera.status === 'active' ? 'success' : 'danger'}>
                      {camera.status === 'active' ? 'Hoạt động' : 'Không hoạt động'}
                    </Badge>
                  </td>
                  <td>{renderConnectionBadge(camera)}</td>
                  <td>{formatDateTime(camera.last_connected)}</td>
                  <td>
                    <Button
                      variant="info"
                      size="sm"
                      className="me-1"
                      onClick={() => handleEdit(camera)}
                    >
                      Sửa
                    </Button>
                    <Button
                      variant={camera.status === 'active' ? 'warning' : 'success'}
                      size="sm"
                      className="me-1"
                      onClick={() => handleToggleActive(camera)}
                    >
                      {camera.status === 'active' ? 'Tắt' : 'Bật'}
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDelete(camera)}
                    >
                      Xóa
                    </Button>
                  </td>
                </tr>
              ))
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
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Tên Camera</Form.Label>
              <Form.Control
                type="text"
                value={cameraName}
                onChange={(e) => setCameraName(e.target.value)}
                placeholder="Nhập tên camera"
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Vị trí</Form.Label>
              <Form.Control
                type="text"
                value={cameraLocation}
                onChange={(e) => setCameraLocation(e.target.value)}
                placeholder="Vị trí lắp đặt (tùy chọn)"
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Loại Camera</Form.Label>
              <Form.Select
                value={cameraType}
                onChange={(e) => setCameraType(e.target.value)}
              >
                <option value="webcam">Webcam (Camera máy tính)</option>
                <option value="droidcam">DroidCam (Camera điện thoại)</option>
                <option value="ipcam">IP Camera</option>
                <option value="rtsp">RTSP Camera</option>
                <option value="mjpeg">MJPEG Camera</option>
                <option value="public_url">Public URL (ngrok, tunnel,...)</option>
              </Form.Select>
            </Form.Group>

            {renderCameraTypeFields()}
            
            <div className="d-flex justify-content-between">
              <Button variant="secondary" onClick={() => setShowModal(false)}>
                Hủy
              </Button>
              <div>
                <Button
                  variant="info"
                  className="me-2"
                  onClick={testConnection}
                  disabled={testingConnection}
                >
                  {testingConnection ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                      />
                      <span className="ms-1">Đang kiểm tra...</span>
                    </>
                  ) : (
                    'Kiểm tra kết nối'
                  )}
                </Button>
                <Button
                  variant="primary"
                  onClick={handleSave}
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
                      <span className="ms-1">Đang lưu...</span>
                    </>
                  ) : (
                    'Lưu Camera'
                  )}
                </Button>
              </div>
            </div>
            
            {renderTestResult()}
          </Form>
        </Modal.Body>
      </Modal>
    </Container>
  );
};

export default CameraManagement; 
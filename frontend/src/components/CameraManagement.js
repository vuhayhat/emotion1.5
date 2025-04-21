import React, { useState, useEffect } from 'react';
import { Container, Button, Table, Modal, Form, Row, Col, Alert, Spinner, Badge } from 'react-bootstrap';
import apiService from '../services/api';
import axios from 'axios';

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
  const [testingConnection, setTestingConnection] = useState(false);

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
  }, []);

  useEffect(() => {
    if (cameras && cameras.length === 0 && !loading && !error) {
      setShowNoCameraMessage(true);
    } else {
      setShowNoCameraMessage(false);
    }
  }, [cameras, loading, error]);

  useEffect(() => {
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
      
      if (response && response.data) {
        if (Array.isArray(response.data)) {
          setCameras(response.data);
        } else if (response.data.cameras) {
          setCameras(response.data.cameras);
        } else if (response.data.camera) {
          setCameras(response.data.camera);
        } else {
          console.warn("Dữ liệu trả về không đúng định dạng:", response.data);
          setCameras([]);
        }
      } else {
        setCameras([]);
      }
    } catch (error) {
      console.error("Error fetching cameras:", error);
      setError('Không thể tải danh sách camera');
      setCameras([]);
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
        setLoading(true);
        const response = await apiService.cameras.delete(camera.id);
        
        if (response.data.success) {
          setSuccess('Camera đã được xóa thành công');
          // Cập nhật danh sách camera sau khi xóa
          setCameras(prevCameras => prevCameras.filter(c => c.id !== camera.id));
        } else {
          setError(response.data.message || 'Không thể xóa camera');
        }
      } catch (err) {
        console.error('Error deleting camera:', err);
        setError(err.response?.data?.message || 'Không thể xóa camera. Vui lòng thử lại.');
      } finally {
        setLoading(false);
      }
    }
  };

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

  const openScheduleModal = (cameraId) => {
    setSelectedCameraId(cameraId);
    setShowScheduleModal(true);
    
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
      setScheduleType('interval');
      setIntervalMinutes(15);
      setScheduleHour('*');
      setScheduleMinute('0');
    }
  };

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
      
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (error) {
      setError('Không thể lưu lịch trình: ' + (error.response?.data?.error || error.message));
      console.error("Error saving schedule:", error);
    }
  };

  const handleDeleteSchedule = async (cameraId) => {
    if (window.confirm('Bạn có chắc muốn xóa lịch trình cho camera này?')) {
      try {
        await apiService.schedules.delete(cameraId);
        loadSchedules();
        setSuccess('Lịch trình đã được xóa thành công');
        
        setTimeout(() => {
          setSuccess(null);
        }, 3000);
      } catch (error) {
        setError('Không thể xóa lịch trình: ' + (error.response?.data?.error || error.message));
        console.error("Error deleting schedule:", error);
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

  const createDefaultCameras = async () => {
    try {
      setLoading(true);
      // Tạo camera mặc định - webcam
      await apiService.cameras.add({
        name: "Default Webcam",
        location: "Local",
        camera_type: "webcam",
        status: "active",
        connection_status: "disconnected"
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
      await axios.put(`http://localhost:5000/api/cameras/${camera.id}`, {
        ...camera,
        status: newStatus
      });
      setSuccess(`Đã ${newStatus === 'active' ? 'kích hoạt' : 'vô hiệu hóa'} camera ${camera.name}`);
      fetchCameras();
    } catch (err) {
      setError('Không thể thay đổi trạng thái camera');
    }
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
                      <Badge bg={camera.status === 'active' ? 'success' : 'danger'}>
                        {camera.status === 'active' ? 'Hoạt động' : 'Không hoạt động'}
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
                      <Button
                        variant="info"
                        size="sm"
                        className="me-1"
                        onClick={() => handleEdit(camera)}
                      >
                        <i className="bi bi-pencil me-1"></i>
                        Sửa
                      </Button>
                      
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
                            <>
                              <i className="bi bi-camera me-1"></i>
                              Chụp ảnh
                            </>
                          )}
                        </Button>
                      )}
                      
                      <Button
                        variant="outline-info"
                        size="sm"
                        className="me-2"
                        onClick={() => testConnection(camera)}
                        disabled={testingConnection}
                      >
                        {testingConnection ? 'Đang kiểm tra...' : 'Kiểm tra kết nối'}
                      </Button>
                      
                      <Button
                        variant={camera.status === 'active' ? 'outline-warning' : 'outline-success'}
                        size="sm"
                        className="me-2"
                        onClick={() => handleToggleActive(camera)}
                      >
                        {camera.status === 'active' ? 'Vô hiệu hóa' : 'Kích hoạt'}
                      </Button>
                      
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(camera)}
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
                            <span className="ms-1">Đang xóa...</span>
                          </>
                        ) : (
                          <>
                            <i className="bi bi-trash me-1"></i>
                            Xóa
                          </>
                        )}
                      </Button>
                    </td>
                  </tr>
                );
              })
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
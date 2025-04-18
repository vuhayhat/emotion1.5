import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Form, Modal, Alert, Spinner, Badge, Row, Col } from 'react-bootstrap';
import axios from 'axios';

const CameraManagement = () => {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  
  // Form state
  const [cameraName, setCameraName] = useState('');
  const [cameraLocation, setCameraLocation] = useState('');
  const [cameraType, setCameraType] = useState('webcam');
  const [ipAddress, setIpAddress] = useState('');
  const [port, setPort] = useState('4747');
  const [testStatus, setTestStatus] = useState('');
  
  const API_URL = 'http://localhost:5000/api';
  
  // Tải danh sách camera
  const fetchCameras = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/cameras`);
      setCameras(response.data || []);
      setError('');
    } catch (err) {
      console.error('Error fetching cameras:', err);
      setError('Không thể tải danh sách camera. Vui lòng thử lại sau.');
    } finally {
      setLoading(false);
    }
  };
  
  // Tải danh sách camera khi component được mount
  useEffect(() => {
    fetchCameras();
  }, []);
  
  // Mở modal để thêm camera mới
  const handleAddNew = () => {
    setEditingCamera(null);
    setCameraName('');
    setCameraLocation('');
    setCameraType('webcam');
    setIpAddress('');
    setPort('4747');
    setTestStatus('');
    setShowModal(true);
  };
  
  // Mở modal để chỉnh sửa camera
  const handleEdit = (camera) => {
    setEditingCamera(camera);
    setCameraName(camera.name);
    setCameraLocation(camera.location || '');
    setCameraType(camera.camera_type || 'webcam');
    setIpAddress(camera.ip_address || '');
    setPort(camera.port?.toString() || '4747');
    setTestStatus('');
    setShowModal(true);
  };

  // Kiểm tra kết nối camera
  const handleTestConnection = async () => {
    if (cameraType === 'webcam') {
      setTestStatus('success');
      return;
    }

    if (!ipAddress || !port) {
      setTestStatus('error');
      setError('Vui lòng nhập địa chỉ IP và cổng');
      return;
    }

    try {
      setTestStatus('testing');
      const response = await axios.post(`${API_URL}/cameras/test`, {
        type: cameraType,
        ip_address: ipAddress,
        port: parseInt(port)
      });

      if (response.data.connection_status === 'connected') {
        setTestStatus('success');
        setError('');
      } else {
        setTestStatus('error');
        setError('Không thể kết nối đến camera. Vui lòng kiểm tra lại thông tin.');
      }
    } catch (err) {
      setTestStatus('error');
      setError('Lỗi kiểm tra kết nối: ' + (err.response?.data?.message || err.message));
    }
  };
  
  // Lưu camera (thêm mới hoặc cập nhật)
  const handleSave = async () => {
    try {
      if (!cameraName.trim()) {
        setError('Tên camera không được để trống');
        return;
      }

      if (cameraType !== 'webcam' && (!ipAddress || !port)) {
        setError('Vui lòng nhập địa chỉ IP và cổng cho DroidCam/IP Camera');
        return;
      }
      
      setLoading(true);
      
      const cameraData = {
        name: cameraName,
        location: cameraLocation,
        type: cameraType,
        ip_address: cameraType !== 'webcam' ? ipAddress : null,
        port: cameraType !== 'webcam' ? parseInt(port) : null
      };

      if (editingCamera) {
        // Cập nhật camera
        await axios.put(`${API_URL}/cameras/${editingCamera.id}`, cameraData);
      } else {
        // Thêm camera mới
        await axios.post(`${API_URL}/cameras`, cameraData);
      }
      
      // Tải lại danh sách camera
      await fetchCameras();
      
      // Đóng modal
      setShowModal(false);
      setError('');
    } catch (err) {
      console.error('Error saving camera:', err);
      setError(err.response?.data?.error || 'Có lỗi xảy ra khi lưu camera');
    } finally {
      setLoading(false);
    }
  };
  
  // Bật/tắt trạng thái camera
  const handleToggleActive = async (camera) => {
    try {
      setLoading(true);
      await axios.put(`${API_URL}/cameras/${camera.id}`, {
        is_active: !camera.is_active
      });
      
      // Tải lại danh sách camera
      await fetchCameras();
    } catch (err) {
      console.error('Error toggling camera active state:', err);
      setError('Không thể cập nhật trạng thái camera');
    } finally {
      setLoading(false);
    }
  };
  
  // Xóa camera
  const handleDelete = async (camera) => {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa camera "${camera.name}"?`)) {
      return;
    }
    
    try {
      setLoading(true);
      await axios.delete(`${API_URL}/cameras/${camera.id}`);
      
      // Tải lại danh sách camera
      await fetchCameras();
    } catch (err) {
      console.error('Error deleting camera:', err);
      setError('Không thể xóa camera');
    } finally {
      setLoading(false);
    }
  };
  
  // Format thời gian
  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return 'Chưa sử dụng';
    
    const date = new Date(dateTimeStr);
    return date.toLocaleString();
  };
  
  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3>Quản Lý Camera</h3>
        <Button onClick={handleAddNew} variant="primary">Thêm Camera Mới</Button>
      </div>
      
      {error && (
        <Alert variant="danger" className="mb-4" onClose={() => setError('')} dismissible>
          {error}
        </Alert>
      )}
      
      {loading && !cameras.length ? (
        <div className="text-center my-5">
          <Spinner animation="border" />
          <p className="mt-2">Đang tải danh sách camera...</p>
        </div>
      ) : (
        <Card>
          <Card.Body>
            {cameras.length === 0 ? (
              <Alert variant="info">
                Chưa có camera nào được thêm vào hệ thống.
              </Alert>
            ) : (
              <Table responsive hover>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Tên</th>
                    <th>Loại</th>
                    <th>Vị trí</th>
                    <th>Trạng thái</th>
                    <th>Địa chỉ</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {cameras.map(camera => (
                    <tr key={camera.id}>
                      <td>{camera.id}</td>
                      <td>{camera.name}</td>
                      <td>{camera.camera_type === 'droidcam' ? 'DroidCam' : camera.camera_type === 'ipcam' ? 'IP Camera' : 'Webcam'}</td>
                      <td>{camera.location || '-'}</td>
                      <td>
                        <Badge bg={camera.connection_status === 'connected' ? 'success' : camera.connection_status === 'error' ? 'danger' : 'warning'}>
                          {camera.connection_status === 'connected' ? 'Đã kết nối' : camera.connection_status === 'error' ? 'Lỗi' : 'Chưa kết nối'}
                        </Badge>
                      </td>
                      <td>
                        {camera.camera_type !== 'webcam' ? `${camera.ip_address}:${camera.port}` : '-'}
                      </td>
                      <td>
                        <Button
                          variant="outline-primary"
                          size="sm"
                          className="me-2"
                          onClick={() => handleEdit(camera)}
                        >
                          Sửa
                        </Button>
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => handleDelete(camera)}
                        >
                          Xóa
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card.Body>
        </Card>
      )}
      
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{editingCamera ? 'Chỉnh Sửa Camera' : 'Thêm Camera Mới'}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Tên Camera</Form.Label>
              <Form.Control
                type="text"
                placeholder="Nhập tên camera"
                value={cameraName}
                onChange={(e) => setCameraName(e.target.value)}
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Loại Camera</Form.Label>
              <Form.Select
                value={cameraType}
                onChange={(e) => setCameraType(e.target.value)}
              >
                <option value="webcam">Webcam</option>
                <option value="droidcam">DroidCam</option>
                <option value="ipcam">IP Camera</option>
              </Form.Select>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Vị Trí</Form.Label>
              <Form.Control
                type="text"
                placeholder="Nhập vị trí đặt camera"
                value={cameraLocation}
                onChange={(e) => setCameraLocation(e.target.value)}
              />
            </Form.Group>

            {cameraType !== 'webcam' && (
              <>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Địa Chỉ IP</Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="Ví dụ: 192.168.1.100"
                        value={ipAddress}
                        onChange={(e) => setIpAddress(e.target.value)}
                      />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Cổng (Port)</Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="Mặc định: 4747"
                        value={port}
                        onChange={(e) => setPort(e.target.value)}
                      />
                    </Form.Group>
                  </Col>
                </Row>
                <div className="mb-3">
                  <Button
                    variant="info"
                    onClick={handleTestConnection}
                    disabled={testStatus === 'testing'}
                  >
                    {testStatus === 'testing' ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        Đang kiểm tra...
                      </>
                    ) : (
                      'Kiểm Tra Kết Nối'
                    )}
                  </Button>
                  {testStatus === 'success' && (
                    <Badge bg="success" className="ms-2">Kết nối thành công!</Badge>
                  )}
                  {testStatus === 'error' && (
                    <Badge bg="danger" className="ms-2">Kết nối thất bại</Badge>
                  )}
                </div>
              </>
            )}
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Hủy
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={loading}>
            {loading ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Đang lưu...
              </>
            ) : (
              'Lưu'
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default CameraManagement; 
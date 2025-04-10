import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Form, Modal, Alert, Spinner, Badge } from 'react-bootstrap';
import axios from 'axios';

const CameraManagement = () => {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  
  // Form state
  const [cameraName, setCameraName] = useState('');
  const [cameraDescription, setCameraDescription] = useState('');
  const [cameraLocation, setCameraLocation] = useState('');
  
  const API_URL = 'http://localhost:5000/api';
  
  // Tải danh sách camera
  const fetchCameras = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/cameras`);
      setCameras(response.data.cameras || []);
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
    setCameraDescription('');
    setCameraLocation('');
    setShowModal(true);
  };
  
  // Mở modal để chỉnh sửa camera
  const handleEdit = (camera) => {
    setEditingCamera(camera);
    setCameraName(camera.name);
    setCameraDescription(camera.description || '');
    setCameraLocation(camera.location || '');
    setShowModal(true);
  };
  
  // Lưu camera (thêm mới hoặc cập nhật)
  const handleSave = async () => {
    try {
      if (!cameraName.trim()) {
        setError('Tên camera không được để trống');
        return;
      }
      
      setLoading(true);
      
      if (editingCamera) {
        // Cập nhật camera
        await axios.put(`${API_URL}/cameras/${editingCamera.id}`, {
          name: cameraName,
          description: cameraDescription,
          location: cameraLocation
        });
      } else {
        // Thêm camera mới
        await axios.post(`${API_URL}/cameras`, {
          name: cameraName,
          description: cameraDescription,
          location: cameraLocation
        });
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
                    <th>Vị trí</th>
                    <th>Trạng thái</th>
                    <th>Lần cuối sử dụng</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {cameras.map(camera => (
                    <tr key={camera.id}>
                      <td>{camera.id}</td>
                      <td>
                        {camera.name}
                        {camera.description && (
                          <div><small className="text-muted">{camera.description}</small></div>
                        )}
                      </td>
                      <td>{camera.location || '-'}</td>
                      <td>
                        <Badge bg={camera.is_active ? 'success' : 'secondary'}>
                          {camera.is_active ? 'Hoạt động' : 'Tạm ngừng'}
                        </Badge>
                      </td>
                      <td>{formatDateTime(camera.last_used)}</td>
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
                          variant={camera.is_active ? 'outline-warning' : 'outline-success'}
                          size="sm"
                          className="me-2"
                          onClick={() => handleToggleActive(camera)}
                        >
                          {camera.is_active ? 'Tạm ngừng' : 'Kích hoạt'}
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
      
      {/* Modal thêm/sửa camera */}
      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{editingCamera ? 'Chỉnh sửa camera' : 'Thêm camera mới'}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Tên camera <span className="text-danger">*</span></Form.Label>
              <Form.Control
                type="text"
                value={cameraName}
                onChange={(e) => setCameraName(e.target.value)}
                placeholder="Nhập tên camera"
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Mô tả</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={cameraDescription}
                onChange={(e) => setCameraDescription(e.target.value)}
                placeholder="Nhập mô tả (tùy chọn)"
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Vị trí</Form.Label>
              <Form.Control
                type="text"
                value={cameraLocation}
                onChange={(e) => setCameraLocation(e.target.value)}
                placeholder="Nhập vị trí camera (tùy chọn)"
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Hủy bỏ
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={loading}>
            {loading ? (
              <>
                <Spinner
                  as="span"
                  animation="border"
                  size="sm"
                  role="status"
                  aria-hidden="true"
                  className="me-2"
                />
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
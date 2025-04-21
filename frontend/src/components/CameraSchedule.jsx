import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Table, Alert, Spinner } from 'react-bootstrap';
import axios from 'axios';

const CameraSchedule = ({ show, onHide, cameraId }) => {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    type: 'interval',
    interval_minutes: 5,
    hour: '00',
    minute: '00',
    is_active: true
  });

  useEffect(() => {
    if (show && cameraId) {
      fetchSchedules();
    }
  }, [show, cameraId]);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/cameras/${cameraId}/schedules`);
      setSchedules(response.data);
      setError('');
    } catch (err) {
      setError('Không thể tải lịch trình. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      await axios.post(`/api/cameras/${cameraId}/schedules`, formData);
      await fetchSchedules();
      setShowAddForm(false);
      setFormData({
        type: 'interval',
        interval_minutes: 5,
        hour: '00',
        minute: '00',
        is_active: true
      });
    } catch (err) {
      setError('Không thể tạo lịch trình. Vui lòng kiểm tra lại thông tin.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (scheduleId) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa lịch trình này?')) return;
    
    try {
      setLoading(true);
      await axios.delete(`/api/cameras/${cameraId}/schedules/${scheduleId}`);
      await fetchSchedules();
    } catch (err) {
      setError('Không thể xóa lịch trình. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (scheduleId, currentStatus) => {
    try {
      setLoading(true);
      await axios.put(`/api/cameras/${cameraId}/schedules/${scheduleId}`, {
        is_active: !currentStatus
      });
      await fetchSchedules();
    } catch (err) {
      setError('Không thể cập nhật trạng thái. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal show={show} onHide={onHide} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Quản lý lịch trình chụp ảnh</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        
        {!showAddForm ? (
          <>
            <Button 
              variant="primary" 
              onClick={() => setShowAddForm(true)}
              className="mb-3"
            >
              Thêm lịch trình mới
            </Button>

            {loading ? (
              <div className="text-center">
                <Spinner animation="border" />
              </div>
            ) : (
              <Table striped bordered hover>
                <thead>
                  <tr>
                    <th>Loại</th>
                    <th>Chi tiết</th>
                    <th>Trạng thái</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {schedules.map(schedule => (
                    <tr key={schedule.id}>
                      <td>
                        {schedule.type === 'interval' ? 'Định kỳ' : 'Hẹn giờ'}
                      </td>
                      <td>
                        {schedule.type === 'interval' 
                          ? `${schedule.interval_minutes} phút/lần`
                          : `${schedule.hour}:${schedule.minute}`
                        }
                      </td>
                      <td>
                        <Form.Check
                          type="switch"
                          checked={schedule.is_active}
                          onChange={() => handleToggleActive(schedule.id, schedule.is_active)}
                          label={schedule.is_active ? 'Đang hoạt động' : 'Tạm dừng'}
                        />
                      </td>
                      <td>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleDelete(schedule.id)}
                        >
                          Xóa
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </>
        ) : (
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Loại lịch trình</Form.Label>
              <Form.Select
                value={formData.type}
                onChange={(e) => setFormData({...formData, type: e.target.value})}
              >
                <option value="interval">Định kỳ (theo phút)</option>
                <option value="time">Hẹn giờ cụ thể</option>
              </Form.Select>
            </Form.Group>

            {formData.type === 'interval' ? (
              <Form.Group className="mb-3">
                <Form.Label>Khoảng thời gian (phút)</Form.Label>
                <Form.Control
                  type="number"
                  min="1"
                  value={formData.interval_minutes}
                  onChange={(e) => setFormData({...formData, interval_minutes: parseInt(e.target.value)})}
                />
              </Form.Group>
            ) : (
              <>
                <Form.Group className="mb-3">
                  <Form.Label>Giờ</Form.Label>
                  <Form.Control
                    type="number"
                    min="0"
                    max="23"
                    value={formData.hour}
                    onChange={(e) => setFormData({...formData, hour: e.target.value.padStart(2, '0')})}
                  />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>Phút</Form.Label>
                  <Form.Control
                    type="number"
                    min="0"
                    max="59"
                    value={formData.minute}
                    onChange={(e) => setFormData({...formData, minute: e.target.value.padStart(2, '0')})}
                  />
                </Form.Group>
              </>
            )}

            <div className="d-flex justify-content-end gap-2">
              <Button variant="secondary" onClick={() => setShowAddForm(false)}>
                Hủy
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <Spinner animation="border" size="sm" />
                ) : (
                  'Lưu lịch trình'
                )}
              </Button>
            </div>
          </Form>
        )}
      </Modal.Body>
    </Modal>
  );
};

export default CameraSchedule; 
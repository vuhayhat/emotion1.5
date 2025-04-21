import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Table, Alert } from 'react-bootstrap';
import axios from 'axios';

const CameraSchedule = ({ show, onHide, cameraId }) => {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({
    type: 'interval',
    interval_minutes: 5,
    hour: 0,
    minute: 0,
    is_active: true
  });

  // Fetch schedules when component mounts
  useEffect(() => {
    if (show) {
      fetchSchedules();
    }
  }, [show, cameraId]);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/cameras/${cameraId}/schedules`);
      setSchedules(response.data.schedules);
      setError('');
    } catch (err) {
      setError('Không thể tải lịch trình: ' + err.message);
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
      setShowAddModal(false);
      setFormData({
        type: 'interval',
        interval_minutes: 5,
        hour: 0,
        minute: 0,
        is_active: true
      });
    } catch (err) {
      setError('Không thể tạo lịch trình: ' + err.message);
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
      setError('Không thể xóa lịch trình: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleActive = async (schedule) => {
    try {
      setLoading(true);
      await axios.put(`/api/cameras/${cameraId}/schedules/${schedule.id}`, {
        ...schedule,
        is_active: !schedule.is_active
      });
      await fetchSchedules();
    } catch (err) {
      setError('Không thể cập nhật trạng thái: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Modal show={show} onHide={onHide} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Quản lý lịch trình chụp ảnh</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {error && <Alert variant="danger">{error}</Alert>}
          
          <Button 
            variant="primary" 
            onClick={() => setShowAddModal(true)}
            className="mb-3"
          >
            Thêm lịch trình mới
          </Button>

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
                  <td>{schedule.type === 'interval' ? 'Định kỳ' : 'Hẹn giờ'}</td>
                  <td>
                    {schedule.type === 'interval' 
                      ? `${schedule.interval_minutes} phút/lần`
                      : `${schedule.hour}:${schedule.minute.toString().padStart(2, '0')}`
                    }
                  </td>
                  <td>
                    <Form.Check
                      type="switch"
                      checked={schedule.is_active}
                      onChange={() => toggleActive(schedule)}
                      disabled={loading}
                    />
                  </td>
                  <td>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDelete(schedule.id)}
                      disabled={loading}
                    >
                      Xóa
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Modal.Body>
      </Modal>

      <Modal show={showAddModal} onHide={() => setShowAddModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Thêm lịch trình mới</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Loại lịch trình</Form.Label>
              <Form.Select
                value={formData.type}
                onChange={(e) => setFormData({...formData, type: e.target.value})}
              >
                <option value="interval">Định kỳ</option>
                <option value="cron">Hẹn giờ</option>
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
                    onChange={(e) => setFormData({...formData, hour: parseInt(e.target.value)})}
                  />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>Phút</Form.Label>
                  <Form.Control
                    type="number"
                    min="0"
                    max="59"
                    value={formData.minute}
                    onChange={(e) => setFormData({...formData, minute: parseInt(e.target.value)})}
                  />
                </Form.Group>
              </>
            )}

            <Button variant="primary" type="submit" disabled={loading}>
              Thêm lịch trình
            </Button>
          </Form>
        </Modal.Body>
      </Modal>
    </>
  );
};

export default CameraSchedule; 
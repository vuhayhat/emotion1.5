import React, { useState, useEffect } from 'react';
import { Modal, Form, Button, Row, Col, Alert } from 'react-bootstrap';

const CameraSettings = ({ show, onHide, camera, onSave }) => {
  const [settings, setSettings] = useState({
    cameraType: 'webcam',
    ipAddress: '',
    port: '',
    path: '/video',
    captureInterval: 2,
    enableEmotionDetection: true
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (camera) {
      setSettings({
        cameraType: camera.camera_type || 'webcam',
        ipAddress: camera.ip_address || '',
        port: camera.port || '',
        path: camera.path || '/video',
        captureInterval: camera.capture_interval || 2,
        enableEmotionDetection: camera.enable_emotion_detection !== false
      });
    }
  }, [camera]);

  const validateForm = () => {
    const newErrors = {};
    
    if (settings.cameraType === 'ipcam') {
      if (!settings.ipAddress) {
        newErrors.ipAddress = 'Vui lòng nhập địa chỉ IP';
      } else if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(settings.ipAddress)) {
        newErrors.ipAddress = 'Địa chỉ IP không hợp lệ';
      }

      if (!settings.port) {
        newErrors.port = 'Vui lòng nhập cổng';
      } else if (!/^\d+$/.test(settings.port)) {
        newErrors.port = 'Cổng phải là số';
      }

      if (!settings.path) {
        newErrors.path = 'Vui lòng nhập đường dẫn';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validateForm()) {
      onSave(camera.id, settings);
      onHide();
    }
  };

  const handleChange = (field, value) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <Modal show={show} onHide={onHide} centered size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Cài đặt camera: {camera?.name}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          <Form.Group as={Row} className="mb-3">
            <Form.Label column sm={4}>
              Loại camera
            </Form.Label>
            <Col sm={8}>
              <Form.Select
                value={settings.cameraType}
                onChange={(e) => handleChange('cameraType', e.target.value)}
              >
                <option value="webcam">CAMWEB</option>
                <option value="ipcam">IPCAM</option>
              </Form.Select>
            </Col>
          </Form.Group>

          {settings.cameraType === 'ipcam' && (
            <>
              <Form.Group as={Row} className="mb-3">
                <Form.Label column sm={4}>
                  Địa chỉ IP
                </Form.Label>
                <Col sm={8}>
                  <Form.Control
                    type="text"
                    value={settings.ipAddress}
                    onChange={(e) => handleChange('ipAddress', e.target.value)}
                    isInvalid={!!errors.ipAddress}
                    placeholder="Ví dụ: 192.168.1.100"
                  />
                  <Form.Control.Feedback type="invalid">
                    {errors.ipAddress}
                  </Form.Control.Feedback>
                </Col>
              </Form.Group>

              <Form.Group as={Row} className="mb-3">
                <Form.Label column sm={4}>
                  Cổng
                </Form.Label>
                <Col sm={8}>
                  <Form.Control
                    type="text"
                    value={settings.port}
                    onChange={(e) => handleChange('port', e.target.value)}
                    isInvalid={!!errors.port}
                    placeholder="Ví dụ: 8080"
                  />
                  <Form.Control.Feedback type="invalid">
                    {errors.port}
                  </Form.Control.Feedback>
                </Col>
              </Form.Group>

              <Form.Group as={Row} className="mb-3">
                <Form.Label column sm={4}>
                  Đường dẫn
                </Form.Label>
                <Col sm={8}>
                  <Form.Control
                    type="text"
                    value={settings.path}
                    onChange={(e) => handleChange('path', e.target.value)}
                    isInvalid={!!errors.path}
                    placeholder="Ví dụ: /video"
                  />
                  <Form.Control.Feedback type="invalid">
                    {errors.path}
                  </Form.Control.Feedback>
                </Col>
              </Form.Group>
            </>
          )}

          <Form.Group as={Row} className="mb-3">
            <Form.Label column sm={4}>
              Tốc độ chụp ảnh (giây)
            </Form.Label>
            <Col sm={8}>
              <Form.Control
                type="number"
                min="1"
                max="10"
                value={settings.captureInterval}
                onChange={(e) => handleChange('captureInterval', parseInt(e.target.value))}
              />
            </Col>
          </Form.Group>

          <Form.Group as={Row} className="mb-3">
            <Form.Label column sm={4}>
              Bật nhận diện cảm xúc
            </Form.Label>
            <Col sm={8}>
              <Form.Check
                type="switch"
                checked={settings.enableEmotionDetection}
                onChange={(e) => handleChange('enableEmotionDetection', e.target.checked)}
              />
            </Col>
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Hủy
        </Button>
        <Button variant="primary" onClick={handleSave}>
          Lưu
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default CameraSettings; 
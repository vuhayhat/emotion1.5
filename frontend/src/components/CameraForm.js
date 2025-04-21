import React, { useState } from 'react';
import { Form, Button, Alert, Modal } from 'react-bootstrap';
import axios from 'axios';

const CameraForm = ({ show, handleClose, onSuccess, editCamera = null }) => {
    const [formData, setFormData] = useState({
        name: editCamera?.name || '',
        location: editCamera?.location || '',
        camera_type: editCamera?.camera_type || 'webcam',
        ip_address: editCamera?.ip_address || '',
        port: editCamera?.port || '',
        stream_url: editCamera?.stream_url || ''
    });
    
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const validateForm = () => {
        if (!formData.name.trim()) {
            setError('Vui lòng nhập tên camera');
            return false;
        }
        
        if (formData.camera_type === 'ipcam') {
            if (!formData.ip_address) {
                setError('Vui lòng nhập địa chỉ IP cho IP Camera');
                return false;
            }
            if (!formData.port) {
                setError('Vui lòng nhập port cho IP Camera');
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
        
        try {
            const url = editCamera 
                ? `http://localhost:5000/api/cameras/${editCamera.id}`
                : 'http://localhost:5000/api/cameras';
                
            const method = editCamera ? 'put' : 'post';
            
            const response = await axios[method](url, formData);
            
            if (response.data.success) {
                onSuccess(response.data.camera);
                handleClose();
            } else {
                setError(response.data.message || 'Có lỗi xảy ra');
            }
        } catch (err) {
            setError(err.response?.data?.message || 'Không thể kết nối đến server');
        } finally {
            setLoading(false);
        }
    };

    const testConnection = async () => {
        if (!editCamera) return;
        
        setLoading(true);
        try {
            const response = await axios.post(
                `http://localhost:5000/api/cameras/${editCamera.id}/test-connection`
            );
            setError(response.data.message);
        } catch (err) {
            setError('Không thể kiểm tra kết nối camera');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose}>
            <Modal.Header closeButton>
                <Modal.Title>
                    {editCamera ? 'Chỉnh sửa Camera' : 'Thêm Camera Mới'}
                </Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form onSubmit={handleSubmit}>
                    {error && <Alert variant="danger">{error}</Alert>}
                    
                    <Form.Group className="mb-3">
                        <Form.Label>Tên camera *</Form.Label>
                        <Form.Control
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            required
                        />
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label>Vị trí</Form.Label>
                        <Form.Control
                            type="text"
                            name="location"
                            value={formData.location}
                            onChange={handleChange}
                        />
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label>Loại camera</Form.Label>
                        <Form.Select
                            name="camera_type"
                            value={formData.camera_type}
                            onChange={handleChange}
                        >
                            <option value="webcam">Webcam</option>
                            <option value="ipcam">IP Camera</option>
                            <option value="droidcam">DroidCam</option>
                        </Form.Select>
                    </Form.Group>

                    {formData.camera_type !== 'webcam' && (
                        <>
                            <Form.Group className="mb-3">
                                <Form.Label>Địa chỉ IP</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="ip_address"
                                    value={formData.ip_address}
                                    onChange={handleChange}
                                    placeholder="Ví dụ: 192.168.1.100"
                                />
                            </Form.Group>

                            <Form.Group className="mb-3">
                                <Form.Label>Port</Form.Label>
                                <Form.Control
                                    type="number"
                                    name="port"
                                    value={formData.port}
                                    onChange={handleChange}
                                    placeholder="Ví dụ: 8080"
                                />
                            </Form.Group>

                            <Form.Group className="mb-3">
                                <Form.Label>URL Stream (tùy chọn)</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="stream_url"
                                    value={formData.stream_url}
                                    onChange={handleChange}
                                    placeholder="Ví dụ: /video"
                                />
                            </Form.Group>
                        </>
                    )}
                </Form>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose}>
                    Hủy
                </Button>
                {editCamera && (
                    <Button 
                        variant="info" 
                        onClick={testConnection}
                        disabled={loading}
                    >
                        Kiểm tra kết nối
                    </Button>
                )}
                <Button 
                    variant="primary" 
                    onClick={handleSubmit}
                    disabled={loading}
                >
                    {loading ? 'Đang xử lý...' : (editCamera ? 'Cập nhật' : 'Thêm mới')}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default CameraForm; 
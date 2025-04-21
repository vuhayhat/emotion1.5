import React, { useState, useEffect } from 'react';
import { Table, Button, Container, Row, Col } from 'react-bootstrap';
import axios from 'axios';
import CameraForm from './CameraForm';

const CameraList = () => {
    const [cameras, setCameras] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [editCamera, setEditCamera] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchCameras = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/cameras');
            setCameras(response.data.cameras || []);
        } catch (err) {
            setError('Không thể tải danh sách camera');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCameras();
    }, []);

    const handleDelete = async (id) => {
        if (!window.confirm('Bạn có chắc chắn muốn xóa camera này?')) return;
        
        try {
            await axios.delete(`http://localhost:5000/api/cameras/${id}`);
            setCameras(cameras.filter(cam => cam.id !== id));
        } catch (err) {
            setError('Không thể xóa camera');
        }
    };

    const handleEdit = (camera) => {
        setEditCamera(camera);
        setShowForm(true);
    };

    const handleFormSuccess = () => {
        setShowForm(false);
        setEditCamera(null);
        fetchCameras();
    };

    const handleCloseForm = () => {
        setShowForm(false);
        setEditCamera(null);
    };

    if (loading) return <div>Đang tải...</div>;

    return (
        <Container>
            <Row className="mb-3">
                <Col>
                    <h2>Danh sách Camera</h2>
                </Col>
                <Col xs="auto">
                    <Button 
                        variant="primary" 
                        onClick={() => setShowForm(true)}
                    >
                        Thêm Camera
                    </Button>
                </Col>
            </Row>

            {error && <div className="alert alert-danger">{error}</div>}

            <Table striped bordered hover>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Tên</th>
                        <th>Vị trí</th>
                        <th>Loại</th>
                        <th>Trạng thái</th>
                        <th>Thao tác</th>
                    </tr>
                </thead>
                <tbody>
                    {cameras.map(camera => (
                        <tr key={camera.id}>
                            <td>{camera.id}</td>
                            <td>{camera.name}</td>
                            <td>{camera.location || '-'}</td>
                            <td>{camera.camera_type}</td>
                            <td>
                                <span className={`badge bg-${camera.is_connected ? 'success' : 'danger'}`}>
                                    {camera.is_connected ? 'Đã kết nối' : 'Chưa kết nối'}
                                </span>
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
                                    onClick={() => handleDelete(camera.id)}
                                >
                                    Xóa
                                </Button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </Table>

            <CameraForm
                show={showForm}
                handleClose={handleCloseForm}
                onSuccess={handleFormSuccess}
                editCamera={editCamera}
            />
        </Container>
    );
};

export default CameraList; 
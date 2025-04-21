import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Button, Spinner } from 'react-bootstrap';
import axios from 'axios';
import './Dashboard.css';

const Dashboard = () => {
    const [cameras, setCameras] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [defaultWebcamActive, setDefaultWebcamActive] = useState(false);
    const defaultWebcamRef = useRef(null);

    useEffect(() => {
        fetchCameras();
        initializeDefaultWebcam();
    }, []);

    const fetchCameras = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/cameras');
            setCameras(response.data.cameras || []);
        } catch (err) {
            setError('Không thể tải danh sách camera');
            console.error('Error fetching cameras:', err);
        } finally {
            setLoading(false);
        }
    };

    const initializeDefaultWebcam = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (defaultWebcamRef.current) {
                defaultWebcamRef.current.srcObject = stream;
                setDefaultWebcamActive(true);
            }
        } catch (err) {
            console.error('Không thể truy cập webcam:', err);
            setDefaultWebcamActive(false);
        }
    };

    const handleCameraSettings = (cameraId) => {
        // TODO: Implement camera settings
        console.log('Opening settings for camera:', cameraId);
    };

    const renderCameraCard = (camera, isDefault = false) => {
        return (
            <Card className="mb-4 camera-card">
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>{isDefault ? 'Camera Mặc Định' : camera.name}</strong>
                        {!isDefault && camera.location && ` - ${camera.location}`}
                    </div>
                    <Button 
                        variant="outline-primary" 
                        size="sm"
                        onClick={() => handleCameraSettings(isDefault ? 'default' : camera.id)}
                    >
                        Cài đặt
                    </Button>
                </Card.Header>
                <Card.Body className="camera-feed">
                    {isDefault ? (
                        <video
                            ref={defaultWebcamRef}
                            autoPlay
                            playsInline
                            muted
                            className="camera-video"
                        />
                    ) : (
                        <div className="camera-placeholder">
                            <div className="camera-placeholder-content">
                                <i className="bi bi-camera-video"></i>
                                <p>Camera {camera.id}</p>
                                <small>{camera.stream_url || 'Chưa có URL stream'}</small>
                            </div>
                        </div>
                    )}
                </Card.Body>
                <Card.Footer>
                    <small className={`text-${isDefault ? (defaultWebcamActive ? 'success' : 'danger') : (camera.status === 'active' ? 'success' : 'danger')}`}>
                        Trạng thái: {isDefault ? (defaultWebcamActive ? 'Đang hoạt động' : 'Không hoạt động') : (camera.status === 'active' ? 'Đang hoạt động' : 'Không hoạt động')}
                    </small>
                </Card.Footer>
            </Card>
        );
    };

    if (loading) {
        return (
            <div className="text-center my-5">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Đang tải...</span>
                </Spinner>
            </div>
        );
    }

    return (
        <Container fluid className="py-4">
            <h2 className="mb-4">Giám Sát Camera</h2>
            
            {error && (
                <div className="alert alert-danger" role="alert">
                    {error}
                </div>
            )}

            <Row>
                {/* Camera mặc định */}
                <Col md={6} lg={4}>
                    {renderCameraCard(null, true)}
                </Col>

                {/* Các camera từ database */}
                {cameras.map(camera => (
                    <Col key={camera.id} md={6} lg={4}>
                        {renderCameraCard(camera)}
                    </Col>
                ))}
            </Row>
        </Container>
    );
};

export default Dashboard; 
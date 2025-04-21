import React, { useState, useEffect } from 'react';
import { Container, Table, Form, Button, Row, Col, Card, Spinner } from 'react-bootstrap';
import axios from 'axios';

const EmotionHistory = () => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        camera_id: '',
        start_date: '',
        end_date: '',
        emotion: ''
    });

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([key, value]) => {
                if (value) params.append(key, value);
            });

            const response = await axios.get(`http://localhost:5000/api/emotions?${params}`);
            setHistory(response.data.emotions || []);
        } catch (err) {
            setError('Không thể tải lịch sử nhận diện');
            console.error('Error fetching history:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleFilterChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        fetchHistory();
    };

    const formatDateTime = (timestamp) => {
        return new Date(timestamp).toLocaleString('vi-VN');
    };

    return (
        <Container className="py-4">
            <h2 className="mb-4">Lịch Sử Nhận Diện Cảm Xúc</h2>
            
            <Card className="mb-4">
                <Card.Body>
                    <Form onSubmit={handleSubmit}>
                        <Row>
                            <Col md={3}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Camera</Form.Label>
                                    <Form.Select
                                        name="camera_id"
                                        value={filters.camera_id}
                                        onChange={handleFilterChange}
                                    >
                                        <option value="">Tất cả camera</option>
                                        <option value="1">Camera 1</option>
                                        <option value="2">Camera 2</option>
                                    </Form.Select>
                                </Form.Group>
                            </Col>
                            <Col md={3}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Từ ngày</Form.Label>
                                    <Form.Control
                                        type="date"
                                        name="start_date"
                                        value={filters.start_date}
                                        onChange={handleFilterChange}
                                    />
                                </Form.Group>
                            </Col>
                            <Col md={3}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Đến ngày</Form.Label>
                                    <Form.Control
                                        type="date"
                                        name="end_date"
                                        value={filters.end_date}
                                        onChange={handleFilterChange}
                                    />
                                </Form.Group>
                            </Col>
                            <Col md={3}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Cảm xúc</Form.Label>
                                    <Form.Select
                                        name="emotion"
                                        value={filters.emotion}
                                        onChange={handleFilterChange}
                                    >
                                        <option value="">Tất cả cảm xúc</option>
                                        <option value="happy">Vui vẻ</option>
                                        <option value="sad">Buồn</option>
                                        <option value="angry">Giận dữ</option>
                                        <option value="neutral">Bình thường</option>
                                    </Form.Select>
                                </Form.Group>
                            </Col>
                        </Row>
                        <div className="text-end">
                            <Button type="submit" variant="primary">
                                Lọc Kết Quả
                            </Button>
                        </div>
                    </Form>
                </Card.Body>
            </Card>

            {loading ? (
                <div className="text-center my-5">
                    <Spinner animation="border" role="status">
                        <span className="visually-hidden">Đang tải...</span>
                    </Spinner>
                </div>
            ) : error ? (
                <div className="alert alert-danger">{error}</div>
            ) : (
                <Table striped bordered hover responsive>
                    <thead>
                        <tr>
                            <th>Thời gian</th>
                            <th>Camera</th>
                            <th>Cảm xúc</th>
                            <th>Độ chính xác</th>
                            <th>Hình ảnh</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history.length === 0 ? (
                            <tr>
                                <td colSpan="5" className="text-center">
                                    Không có dữ liệu
                                </td>
                            </tr>
                        ) : (
                            history.map((record) => (
                                <tr key={record.id}>
                                    <td>{formatDateTime(record.timestamp)}</td>
                                    <td>{record.camera_name || `Camera ${record.camera_id}`}</td>
                                    <td>{record.dominant_emotion}</td>
                                    <td>
                                        {record.emotion_scores && 
                                            `${(record.emotion_scores[record.dominant_emotion] * 100).toFixed(1)}%`}
                                    </td>
                                    <td>
                                        {record.processed_image_base64 && (
                                            <img 
                                                src={`data:image/jpeg;base64,${record.processed_image_base64}`}
                                                alt="Kết quả nhận diện"
                                                style={{ height: '100px' }}
                                            />
                                        )}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </Table>
            )}
        </Container>
    );
};

export default EmotionHistory; 
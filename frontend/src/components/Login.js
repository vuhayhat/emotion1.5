import React, { useState, useEffect } from 'react';
import { Container, Form, Button, Alert, Card } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import authService from '../services/auth';
import './Login.css';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        // Nếu đã đăng nhập, chuyển hướng về trang chủ
        if (authService.isAuthenticated()) {
            navigate('/');
        }
    }, [navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await authService.login(username, password);
            if (response.success) {
                navigate('/');
            } else {
                setError(response.message || 'Đăng nhập thất bại');
            }
        } catch (err) {
            setError(err.message || 'Đăng nhập thất bại. Vui lòng thử lại.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container className="login-container">
            <Card className="login-card">
                <Card.Header className="text-center">
                    <h2>Đăng Nhập</h2>
                </Card.Header>
                <Card.Body>
                    {error && (
                        <Alert variant="danger" onClose={() => setError('')} dismissible>
                            {error}
                        </Alert>
                    )}
                    <Form onSubmit={handleSubmit}>
                        <Form.Group className="mb-3">
                            <Form.Label>Tên đăng nhập</Form.Label>
                            <Form.Control
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Nhập tên đăng nhập"
                                required
                                disabled={loading}
                            />
                        </Form.Group>

                        <Form.Group className="mb-4">
                            <Form.Label>Mật khẩu</Form.Label>
                            <Form.Control
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Nhập mật khẩu"
                                required
                                disabled={loading}
                            />
                        </Form.Group>

                        <div className="d-grid">
                            <Button 
                                variant="primary" 
                                type="submit"
                                disabled={loading}
                            >
                                {loading ? 'Đang đăng nhập...' : 'Đăng Nhập'}
                            </Button>
                        </div>
                    </Form>
                </Card.Body>
            </Card>
        </Container>
    );
};

export default Login; 
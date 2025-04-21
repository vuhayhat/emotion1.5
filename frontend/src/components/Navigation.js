import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Navbar, Nav, Container, Button } from 'react-bootstrap';
import authService from '../services/auth';

const Navigation = () => {
    const navigate = useNavigate();
    const currentUser = authService.getCurrentUser();
    const isAuthenticated = authService.isAuthenticated();

    const handleLogout = () => {
        authService.logout();
        navigate('/login');
    };

    return (
        <Navbar bg="dark" variant="dark" expand="lg">
            <Container>
                <Navbar.Brand as={Link} to="/">Hệ Thống Nhận Diện Cảm Xúc</Navbar.Brand>
                <Navbar.Toggle aria-controls="basic-navbar-nav" />
                <Navbar.Collapse id="basic-navbar-nav">
                    <Nav className="me-auto">
                        {isAuthenticated && (
                            <>
                                <Nav.Link as={Link} to="/">Trang Chủ</Nav.Link>
                                <Nav.Link as={Link} to="/quanlycam">Quản Lý Camera</Nav.Link>
                                <Nav.Link as={Link} to="/lichsu">Lịch Sử Nhận Diện</Nav.Link>
                            </>
                        )}
                    </Nav>
                    <Nav>
                        {isAuthenticated ? (
                            <div className="d-flex align-items-center">
                                <span className="text-light me-3">
                                    Xin chào, {currentUser?.full_name || currentUser?.username}
                                </span>
                                <Button 
                                    variant="outline-light" 
                                    size="sm"
                                    onClick={handleLogout}
                                >
                                    Đăng Xuất
                                </Button>
                            </div>
                        ) : (
                            <Nav.Link as={Link} to="/login">Đăng Nhập</Nav.Link>
                        )}
                    </Nav>
                </Navbar.Collapse>
            </Container>
        </Navbar>
    );
};

export default Navigation; 
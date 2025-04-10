import React from 'react';
import { Container, Row, Col, Button } from 'react-bootstrap';
import './Header.css';

const Header = ({ user, onLogout }) => {
  return (
    <header className="app-header">
      <Container>
        <Row className="align-items-center">
          <Col md={8}>
            <h1 className="app-title">Hệ Thống Nhận Diện Cảm Xúc</h1>
            <p className="app-subtitle">
              Phân tích cảm xúc khuôn mặt theo thời gian thực từ nhiều nguồn camera
            </p>
          </Col>
          <Col md={4} className="text-end">
            <div className="user-info">
              <span className="me-3">
                Xin chào, <strong>{user.username}</strong>
              </span>
              <Button 
                variant="outline-light" 
                size="sm"
                onClick={onLogout}
              >
                Đăng xuất
              </Button>
            </div>
          </Col>
        </Row>
      </Container>
    </header>
  );
};

export default Header;

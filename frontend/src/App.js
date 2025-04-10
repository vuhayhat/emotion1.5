import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Nav } from 'react-bootstrap';
import CameraCapture from './components/CameraCapture';
import EmotionHistory from './components/EmotionHistory';
import CameraManagement from './components/CameraManagement';
import Header from './components/Header';
import Login from './components/Login';
import axios from 'axios';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('camera');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Kiểm tra trạng thái đăng nhập khi component mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      // Thêm token vào header cho tất cả request
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      // Kiểm tra token
      axios.get('/api/auth/verify')
        .then(response => {
          setUser(response.data.user);
        })
        .catch(() => {
          localStorage.removeItem('token');
          delete axios.defaults.headers.common['Authorization'];
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  if (loading) {
    return (
      <div className="text-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="App">
      <Header user={user} onLogout={handleLogout} />
      <Container>
        <Nav 
          variant="tabs" 
          activeKey={activeTab}
          onSelect={(selectedKey) => setActiveTab(selectedKey)}
          className="mb-4"
        >
          <Nav.Item>
            <Nav.Link eventKey="camera">Camera Nhận Diện</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="history">Lịch Sử Cảm Xúc</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="manage">Quản Lý Camera</Nav.Link>
          </Nav.Item>
        </Nav>

        {activeTab === 'camera' ? (
          <Row>
            <Col>
              <CameraCapture />
            </Col>
          </Row>
        ) : activeTab === 'history' ? (
          <Row>
            <Col>
              <EmotionHistory />
            </Col>
          </Row>
        ) : (
          <Row>
            <Col>
              <CameraManagement />
            </Col>
          </Row>
        )}
      </Container>
    </div>
  );
}

export default App; 
import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navigation from './components/Navigation';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import CameraManagement from './components/CameraManagement';
import EmotionHistory from './components/EmotionHistory';
import authService from './services/auth';
import './App.css';

// Protected Route component
const ProtectedRoute = ({ children }) => {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" />;
  }
  return children;
};

const App = () => {
  useEffect(() => {
    // Thiết lập interceptors cho axios
    authService.setupAxiosInterceptors();
  }, []);

  return (
    <Router>
      <div className="App">
        <Navigation />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/quanlycam" element={
            <ProtectedRoute>
              <CameraManagement />
            </ProtectedRoute>
          } />
          <Route path="/lichsu" element={
            <ProtectedRoute>
              <EmotionHistory />
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </Router>
  );
};

export default App; 
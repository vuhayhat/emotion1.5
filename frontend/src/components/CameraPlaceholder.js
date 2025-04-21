import React from 'react';
import { Button, Spinner } from 'react-bootstrap';
import './CameraPlaceholder.css';

const CameraPlaceholder = ({ 
  camera, 
  isActive, 
  onStart, 
  onStop, 
  loading,
  showControls = true 
}) => {
  return (
    <div className="camera-placeholder">
      <div className="camera-placeholder-content">
        <i className="bi bi-camera-video"></i>
        <p>{camera.name}</p>
        <small>{camera.stream_url || 'Chưa có URL stream'}</small>
        
        {showControls && (
          <div className="camera-controls mt-2">
            <Button
              variant={isActive ? "danger" : "success"}
              size="sm"
              onClick={() => isActive ? onStop(camera.id) : onStart(camera.id)}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Spinner
                    as="span"
                    animation="border"
                    size="sm"
                    role="status"
                    aria-hidden="true"
                    className="me-1"
                  />
                  Đang xử lý...
                </>
              ) : (
                <>
                  <i className={`bi ${isActive ? 'bi-stop-circle' : 'bi-play-circle'} me-1`}></i>
                  {isActive ? 'Dừng Camera' : 'Bật Camera'}
                </>
              )}
            </Button>
          </div>
        )}

        {isActive && (
          <div className="camera-status">
            <span className="badge bg-success">
              <i className="bi bi-circle-fill me-1"></i>
              Đang hoạt động
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraPlaceholder; 
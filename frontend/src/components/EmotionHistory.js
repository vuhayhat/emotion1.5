import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Alert, Spinner, Pagination, Form, Image } from 'react-bootstrap';
import axios from 'axios';

// Ánh xạ tên cảm xúc sang tiếng Việt
const emotionLabels = {
  'angry': 'Giận dữ',
  'disgust': 'Ghê tởm',
  'fear': 'Sợ hãi',
  'happy': 'Vui vẻ',
  'sad': 'Buồn bã',
  'surprise': 'Ngạc nhiên',
  'neutral': 'Bình thường'
};

// Màu sắc cho các cảm xúc
const emotionColors = {
  'angry': '#FF0000',
  'disgust': '#800080',
  'fear': '#FFA500',
  'happy': '#00FF00',
  'sad': '#0000FF',
  'surprise': '#FFFF00',
  'neutral': '#808080'
};

const EmotionHistory = () => {
  const [emotions, setEmotions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [selectedCamera, setSelectedCamera] = useState('');
  const [cameras, setCameras] = useState([]);
  const itemsPerPage = 5;

  // Tải danh sách camera khi component mount
  useEffect(() => {
    console.log("Fetching cameras...");
    axios.get('/api/cameras')
      .then(response => {
        console.log("Cameras response:", response.data);
        setCameras(response.data.cameras || []);
      })
      .catch(error => {
        console.error("Error fetching cameras:", error);
        setError("Failed to load cameras: " + (error.response?.data?.error || error.message));
      });
  }, []);

  // Tải lịch sử cảm xúc khi trang hoặc camera thay đổi
  useEffect(() => {
    fetchEmotions();
  }, [page, selectedCamera]);

  const fetchEmotions = async () => {
    setLoading(true);
    try {
      // Tính offset từ page và itemsPerPage
      const offset = (page - 1) * itemsPerPage;
      
      // Xây dựng URL với các tham số
      let url = `/api/emotions?offset=${offset}&limit=${itemsPerPage}&include_images=true`;
      if (selectedCamera) {
        url += `&camera_id=${selectedCamera}`;
      }
      
      console.log("Fetching emotions from:", url);
      
      const response = await axios.get(url);
      console.log("Emotions response:", response.data);
      
      setEmotions(response.data.emotions || []);
      setTotalItems(response.data.total || 0);
      setTotalPages(Math.ceil((response.data.total || 0) / itemsPerPage));
      setError(null);
    } catch (error) {
      console.error("Error fetching emotions:", error);
      setError("Failed to load emotion history: " + (error.response?.data?.error || error.message));
      setEmotions([]);
    } finally {
      setLoading(false);
    }
  };

  // Xử lý thay đổi trang
  const handlePageChange = (newPage) => {
    setPage(newPage);
  };

  // Xử lý thay đổi camera
  const handleCameraChange = (e) => {
    setSelectedCamera(e.target.value);
    setPage(1); // Reset về trang 1 khi thay đổi camera
  };

  // Tìm tên camera theo ID
  const getCameraName = (cameraId) => {
    const camera = cameras.find(c => c.id === cameraId);
    return camera ? camera.name : `Camera ${cameraId}`;
  };

  return (
    <Container className="mt-4">
      <h2 className="mb-4">Lịch sử nhận diện cảm xúc</h2>
      
      {/* Filter controls */}
      <Card className="mb-4">
        <Card.Body>
          <Row>
            <Col md={6}>
              <Form.Group>
                <Form.Label>Lọc theo Camera</Form.Label>
                <Form.Select 
                  value={selectedCamera} 
                  onChange={handleCameraChange}
                >
                  <option value="">Tất cả Camera</option>
                  {cameras.map(camera => (
                    <option key={camera.id} value={camera.id}>
                      {camera.name}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={6} className="d-flex align-items-end">
              <Button variant="primary" onClick={() => fetchEmotions()}>
                Làm mới
              </Button>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Error message */}
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}

      {/* Loading spinner */}
      {loading ? (
        <div className="text-center my-5">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Đang tải...</span>
          </Spinner>
        </div>
      ) : (
        <>
          {/* No data message */}
          {emotions.length === 0 ? (
            <Alert variant="info">
              Không có dữ liệu lịch sử cảm xúc.
            </Alert>
          ) : (
            <>
              {/* Emotion history cards */}
              {emotions.map(emotion => {
                // Parse emotion result if it's a string
                const emotionResult = typeof emotion.emotion_result === 'string' 
                  ? JSON.parse(emotion.emotion_result) 
                  : emotion.emotion_result;
                
                // Format timestamp
                const timestamp = new Date(emotion.timestamp).toLocaleString('vi-VN');
                
                return (
                  <Card key={emotion.id} className="mb-4">
                    <Card.Header>
                      <strong>Thời gian:</strong> {timestamp} | 
                      <strong> Camera:</strong> {getCameraName(emotion.camera_id)}
                    </Card.Header>
                    <Card.Body>
                      <Row>
                        {/* Original image */}
                        <Col md={6}>
                          <h5>Hình ảnh gốc</h5>
                          {emotion.image_base64 ? (
                            <div className="image-container mb-3" style={{ minHeight: '300px' }}>
                              <Image 
                                src={`data:image/jpeg;base64,${emotion.image_base64}`}
                                alt="Original"
                                fluid
                                style={{ maxHeight: '300px', objectFit: 'contain' }}
                              />
                            </div>
                          ) : (
                            <Alert variant="warning">
                              Không tìm thấy hình ảnh gốc
                            </Alert>
                          )}
                        </Col>
                        
                        {/* Processed image */}
                        <Col md={6}>
                          <h5>Hình ảnh đã xử lý</h5>
                          {emotion.processed_image_base64 ? (
                            <div className="image-container mb-3" style={{ minHeight: '300px' }}>
                              <Image 
                                src={`data:image/jpeg;base64,${emotion.processed_image_base64}`}
                                alt="Processed"
                                fluid
                                style={{ maxHeight: '300px', objectFit: 'contain' }}
                              />
                            </div>
                          ) : (
                            <Alert variant="warning">
                              Không tìm thấy hình ảnh đã xử lý
                            </Alert>
                          )}
                        </Col>
                      </Row>
                      
                      {/* Emotion results */}
                      {emotionResult && (
                        <Row className="mt-3">
                          <Col>
                            <h5>Kết quả phân tích cảm xúc</h5>
                            <p><strong>Cảm xúc chính:</strong> {emotionLabels[emotionResult.dominant_emotion] || emotionResult.dominant_emotion}</p>
                            
                            {/* Emotion bars */}
                            <div className="emotion-bars">
                              {Object.entries(emotionResult.emotion_percent || {})
                                .sort(([, a], [, b]) => b - a)
                                .map(([emotion, percent]) => (
                                  <div key={emotion} className="mb-2">
                                    <div className="d-flex justify-content-between mb-1">
                                      <span>{emotionLabels[emotion] || emotion}</span>
                                      <span>{percent}%</span>
                                    </div>
                                    <div className="progress" style={{ height: '20px' }}>
                                      <div
                                        className="progress-bar"
                                        role="progressbar"
                                        style={{
                                          width: `${percent}%`,
                                          backgroundColor: emotionColors[emotion] || '#007bff'
                                        }}
                                        aria-valuenow={percent}
                                        aria-valuemin="0"
                                        aria-valuemax="100"
                                      ></div>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </Col>
                        </Row>
                      )}
                    </Card.Body>
                  </Card>
                );
              })}
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="d-flex justify-content-center mt-4">
                  <Pagination>
                    <Pagination.First
                      onClick={() => handlePageChange(1)}
                      disabled={page === 1}
                    />
                    <Pagination.Prev
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page === 1}
                    />
                    
                    {/* Show page numbers */}
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      // Calculate which pages to show
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (page <= 3) {
                        pageNum = i + 1;
                      } else if (page >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = page - 2 + i;
                      }
                      
                      return (
                        <Pagination.Item
                          key={pageNum}
                          active={pageNum === page}
                          onClick={() => handlePageChange(pageNum)}
                        >
                          {pageNum}
                        </Pagination.Item>
                      );
                    })}
                    
                    <Pagination.Next
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page === totalPages}
                    />
                    <Pagination.Last
                      onClick={() => handlePageChange(totalPages)}
                      disabled={page === totalPages}
                    />
                  </Pagination>
                </div>
              )}
            </>
          )}
        </>
      )}
    </Container>
  );
};

export default EmotionHistory; 
import axios from 'axios';

// Lấy URL API từ biến môi trường hoặc sử dụng giá trị mặc định
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const API_TIMEOUT = parseInt(process.env.REACT_APP_API_TIMEOUT || '10000', 10);

// Tạo instance axios với cấu hình mặc định
const api = axios.create({
  baseURL: API_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Interceptor để thêm token vào header nếu đã đăng nhập
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor xử lý lỗi response
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Xử lý lỗi 401 (Unauthorized) - đăng xuất và chuyển về trang login
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints phù hợp với backend mới
const apiService = {
  // Auth endpoints
  auth: {
    login: (credentials) => api.post('/api/auth/login', credentials),
    register: (userData) => api.post('/api/auth/register', userData),
    getProfile: () => api.get('/api/auth/profile'),
    updateProfile: (profileData) => api.put('/api/auth/profile', profileData),
    verify: () => api.get('/api/auth/verify'),
  },
  
  // Camera endpoints
  cameras: {
    getAll: () => api.get('/api/cameras'),
    getById: (id) => api.get(`/api/cameras/${id}`),
    add: (cameraData) => api.post('/api/cameras', cameraData),
    update: (id, cameraData) => api.put(`/api/cameras/${id}`, cameraData),
    delete: (id) => api.delete(`/api/cameras/${id}`),
    getStream: (id) => api.get(`/api/streams/${id}`),
    startProcess: (id, options = {}) => api.post(`/api/process/${id}`, options),
    stopProcess: (id, options = {}) => api.post(`/api/stop-process/${id}`, options),
    getVideoFeed: (id) => `${API_URL}/api/video-feed/${id}`,
    updateSettings: (cameraId, settings) => api.put(`/api/cameras/${cameraId}/settings`, settings),
    getSettings: (cameraId) => api.get(`/api/cameras/${cameraId}/settings`),
    connectIpCam: (cameraId, settings) => api.post(`/api/cameras/${cameraId}/connect`, settings),
    disconnect: (cameraId) => api.post(`/api/cameras/${cameraId}/disconnect`),
    detectFaces: (cameraId, options) => api.post(`/api/cameras/${cameraId}/detect-faces`, options),
    captureRtsp: (cameraId) => api.post(`/api/cameras/rtsp-capture`, { camera_id: cameraId }),
    testConnection: (cameraId) => api.post(`/api/cameras/${cameraId}/test-connection`),
    startCamera: (cameraId) => api.post(`/api/cameras/${cameraId}/start`),
    stopCamera: (cameraId) => api.post(`/api/cameras/${cameraId}/stop`),
    getStatus: (cameraId) => api.get(`/api/cameras/${cameraId}/status`),
  },
  
  // Camera group endpoints
  cameraGroups: {
    getAll: () => api.get('/api/camera-groups'),
    create: (groupData) => api.post('/api/camera-groups', groupData),
    addCamera: (groupId, cameraId) => api.post(`/api/camera-groups/${groupId}/add-camera`, { camera_id: cameraId }),
    removeCamera: (groupId, cameraId) => api.delete(`/api/camera-groups/${groupId}/remove-camera/${cameraId}`),
  },

  // Emotion detection results
  emotions: {
    getAll: (params) => api.get('/api/results', { params }),
    getImage: (id) => `${API_URL}/api/image/${id}`,
    getProcessedImage: (id) => `${API_URL}/api/processed-image/${id}`,
  },
  
  // Statistics
  statistics: {
    get: (params) => api.get('/api/statistics', { params }),
  },

  // Kiểm tra trạng thái server
  status: () => api.get('/api/status'),

  // Schedule endpoints
  schedules: {
    getAll: () => api.get('/api/cameras/schedule'),
    create: (scheduleData) => api.post('/api/cameras/schedule', scheduleData),
    delete: (cameraId) => api.delete(`/api/cameras/schedule/${cameraId}`),
    getByCameraId: (cameraId) => api.get(`/api/cameras/schedule/${cameraId}`)
  },
};

export default apiService;
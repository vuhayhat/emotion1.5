import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const authService = {
    login: async (username, password) => {
        try {
            const response = await axios.post(`${API_URL}/auth/login`, {
                username,
                password
            });
            
            if (response.data.token) {
                localStorage.setItem('user', JSON.stringify(response.data));
                axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
            }
            
            return response.data;
        } catch (error) {
            throw error.response?.data || { message: 'Lỗi đăng nhập' };
        }
    },

    logout: () => {
        localStorage.removeItem('user');
        delete axios.defaults.headers.common['Authorization'];
    },

    getCurrentUser: () => {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    },

    isAuthenticated: () => {
        const user = authService.getCurrentUser();
        return !!user && !!user.token;
    },

    setupAxiosInterceptors: () => {
        axios.interceptors.request.use(
            (config) => {
                const user = authService.getCurrentUser();
                if (user && user.token) {
                    config.headers['Authorization'] = `Bearer ${user.token}`;
                }
                return config;
            },
            (error) => {
                return Promise.reject(error);
            }
        );

        axios.interceptors.response.use(
            (response) => response,
            (error) => {
                if (error.response?.status === 401) {
                    authService.logout();
                    window.location.href = '/login';
                }
                return Promise.reject(error);
            }
        );
    }
};

export default authService; 
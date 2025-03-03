import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

// Create an axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to add the auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth services
export const authService = {
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  register: async (email, password, plan) => {
    const response = await api.post('/auth/register', { email, password, plan });
    return response.data;
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },
};

// Chat services
export const chatService = {
  sendMessage: async (message, history = []) => {
    const response = await api.post('/chat', { message, history });
    return response.data;
  },
  getHistory: async () => {
    const response = await api.get('/user/history');
    return response.data;
  },
};

// User services
export const userService = {
  getProfile: async () => {
    const response = await api.get('/user/profile');
    return response.data;
  },
  upgradeAccount: async () => {
    const response = await api.post('/user/upgrade');
    return response.data;
  },
};

export default api;
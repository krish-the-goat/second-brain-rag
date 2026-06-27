import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Request interceptor for authorization
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Add API Key for backend auth
  config.headers['X-API-Key'] = import.meta.env.VITE_API_KEY || 'default-secret-key-change-in-prod';
  return config;
});

// Response interceptor for logging and retry on 429
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    console.error('API Error:', error.response?.data || error.message);
    
    const originalRequest = error.config;
    
    if (error.response?.status === 429 && !originalRequest._retry) {
      originalRequest._retry = true;
      console.log('Rate limit exceeded. Retrying in 1 second...');
      
      // Wait for 1 second
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      return api(originalRequest);
    }
    
    return Promise.reject(error);
  }
);

export default api;

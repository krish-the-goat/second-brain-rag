import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

// Request interceptor — always attach the API key.
// In production, Nginx injects X-API-Key server-side via proxy_set_header.
// In dev (vite proxy or direct), we read it from the VITE_API_KEY env var.
// We send it here too so the dev server (which bypasses Nginx) works correctly.
api.interceptors.request.use((config) => {
  const apiKey = import.meta.env.VITE_API_KEY;
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

// Response interceptor — log errors and retry once on 429.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    console.error('API Error:', error.response?.data || error.message);

    const originalRequest = error.config;

    if (error.response?.status === 429 && !originalRequest._retry) {
      originalRequest._retry = true;
      console.warn('Rate limit hit. Retrying in 2 seconds…');
      await new Promise((resolve) => setTimeout(resolve, 2000));
      return api(originalRequest);
    }

    return Promise.reject(error);
  }
);

export default api;

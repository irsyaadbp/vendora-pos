import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/core/stores/auth.store';

const API_VERSION = '/api/v1';

const apiClient = axios.create({
  baseURL: `${process.env.NEXT_PUBLIC_API_URL}${API_VERSION}`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
}> = [];

function processQueue(error: unknown) {
  failedQueue.forEach(({ reject }) => reject(error));
  failedQueue = [];
}

function retryQueue(token: string) {
  failedQueue.forEach(({ resolve }) => resolve(token));
  failedQueue = [];
}

// Request interceptor: attach access token from auth store
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { accessToken } = useAuthStore.getState();
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: on 401, attempt token refresh via proxy, retry original request
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Only attempt refresh on 401 and if we haven't already retried
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Don't attempt refresh on auth endpoints
    const requestUrl = originalRequest.url || '';
    if (requestUrl.includes('/auth/')) {
      return Promise.reject(error);
    }

    // If already refreshing, queue this request
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${token}`;
        }
        return apiClient(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Refresh via the Next.js proxy (updates the HTTP-only cookie too)
      const response = await axios.post('/api/auth/refresh', {}, { withCredentials: true });
      const { access_token } = response.data.data;

      // Update auth store with new token
      const authStore = useAuthStore.getState();
      const currentUser = authStore.user;
      if (currentUser) {
        authStore.setAuth(currentUser, access_token);
      }

      // Retry queued requests with new token
      retryQueue(access_token);

      // Retry original request
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
      }
      return apiClient(originalRequest);
    } catch (refreshError) {
      // Refresh failed: clear auth state and redirect to login
      processQueue(refreshError);
      useAuthStore.getState().clearAuth();

      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }

      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export { apiClient };

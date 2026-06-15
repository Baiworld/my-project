import axios from "axios";
import { useAuthStore } from "@/stores/auth";

const baseURL = import.meta.env.VITE_API_URL || "";

const instance = axios.create({
  baseURL,
  timeout: 30000,
});

instance.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const authStore = useAuthStore();

    // 登录/注册/刷新请求的 401 不重试
    const isAuthEndpoint = originalRequest.url?.includes("/auth/login")
      || originalRequest.url?.includes("/auth/register")
      || originalRequest.url?.includes("/auth/refresh");

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      const success = await authStore.refreshAccessToken();
      if (success) {
        originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`;
        return instance(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);

// 网络/服务器错误自动重试（最多 2 次，递增延迟）
instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    // 仅对 GET 请求做自动重试，避免重复提交
    if (config.method !== "get") return Promise.reject(error);
    // 仅对 5xx 或网络错误重试
    const isRetryable = !error.response || error.response.status >= 500;
    if (!isRetryable) return Promise.reject(error);

    config.__retryCount = config.__retryCount || 0;
    if (config.__retryCount >= 2) return Promise.reject(error);

    config.__retryCount += 1;
    const delay = config.__retryCount * 500;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return instance(config);
  }
);

const api = {
  // ── 通用 HTTP 方法（供 Admin / Query 等页面使用） ──
  get: (url, config) => instance.get(url, config),
  post: (url, data, config) => instance.post(url, data, config),
  put: (url, data, config) => instance.put(url, data, config),
  delete: (url, config) => instance.delete(url, config),

  // ── 命名端点 ──
  auth: {
    login: (username, password) =>
      instance.post("/auth/login", { username, password }),
    register: (username, email, password, confirmPassword) =>
      instance.post("/auth/register", { username, email, password, confirm_password: confirmPassword }),
    logout: () => instance.post("/auth/logout"),
    refresh: () => instance.post("/auth/refresh"),
  },
  recommendations: {
    get: (params) => instance.get("/api/recommendations", { params }),
  },
  metrics: {
    get: (params) => instance.get("/api/metrics", { params }),
  },
  content: {
    getHot: (params) => instance.get("/api/content/hot", { params }),
  },
  users: {
    getProfile: (userId) =>
      instance.get("/api/users/profile", { params: { user_id: userId } }),
  },
  coldstart: {
    getAnalysis: () => instance.get("/api/coldstart/analysis"),
    getStats: () => instance.get("/api/coldstart/stats"),
  },
  region: {
    getHeatmap: () => instance.get("/api/region/heatmap"),
  },
  export: {
    download: async (table, format = "csv") => {
      const response = await instance.get(`/api/export/${table}`, {
        params: { format },
        responseType: "blob",
      });
      return response;
    },
  },
  health: {
    check: () => instance.get("/api/health"),
  },
};

export default api;
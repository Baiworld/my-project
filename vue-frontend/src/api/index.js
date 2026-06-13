import axios from "axios";
import { useAuthStore } from "@/stores/auth";

const baseURL = import.meta.env.VITE_API_URL || "";

const instance = axios.create({
  baseURL,
  timeout: 10000,
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

const api = {
  // ── 通用 HTTP 方法（供 Admin / Query 等页面使用） ──
  get: (url, config) => instance.get(url, config),
  post: (url, data, config) => instance.post(url, data, config),
  put: (url, data, config) => instance.put(url, data, config),
  delete: (url, config) => instance.delete(url, config),

  // ── 命名端点 ──
  auth: {
    login: (account, password) =>
      instance.post("/auth/login", { account, password }),
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
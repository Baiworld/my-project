import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/api";

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref(localStorage.getItem("accessToken") || null);
  const refreshToken = ref(localStorage.getItem("refreshToken") || null);
  const user = ref(JSON.parse(localStorage.getItem("user") || "null"));
  const roles = ref(JSON.parse(localStorage.getItem("roles") || "[]"));

  const isAuthenticated = computed(() => {
    if (!accessToken.value) return false;
    // 检查 JWT 是否过期（简单解码 payload，不验证签名）
    try {
      const payload = JSON.parse(atob(accessToken.value.split(".")[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return !!accessToken.value; // 解析失败时 fallback
    }
  });

  function hasRole(roleName) {
    return roles.value.includes(roleName);
  }

  async function login(account, password) {
    try {
      const response = await api.auth.login(account, password);
      const payload = response.data.data;
      accessToken.value = payload.access_token;
      refreshToken.value = payload.refresh_token;
      user.value = payload.user;
      roles.value = payload.user.roles || [];
      localStorage.setItem("accessToken", accessToken.value);
      localStorage.setItem("refreshToken", refreshToken.value);
      localStorage.setItem("user", JSON.stringify(user.value));
      localStorage.setItem("roles", JSON.stringify(roles.value));
      return true;
    } catch (error) {
      console.error("Login failed:", error);
      return false;
    }
  }

  async function register(username, email, password, confirmPassword) {
    try {
      await api.auth.register(username, email, password, confirmPassword);
      return true;
    } catch (error) {
      console.error("Registration failed:", error);
      return false;
    }
  }

  async function logout() {
    // 先清除本地状态，确保即使 API 失败也能退出
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    roles.value = [];
    localStorage.clear();
    try {
      await api.auth.logout();
    } catch (_) {
      // 忽略 logout API 失败（token 可能已过期）
    }
  }

  async function refreshAccessToken() {
    try {
      const response = await api.auth.refresh();
      const payload = response.data.data;
      accessToken.value = payload.access_token;
      localStorage.setItem("accessToken", accessToken.value);
      return true;
    } catch (error) {
      console.error("Token refresh failed:", error);
      logout();
      return false;
    }
  }

  return {
    accessToken,
    refreshToken,
    user,
    roles,
    isAuthenticated,
    hasRole,
    login,
    register,
    logout,
    refreshAccessToken,
  };
});

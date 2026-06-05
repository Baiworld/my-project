<template>
  <div class="login-page">
    <!-- Animated background orbs -->
    <div class="bg-orbs">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>

    <!-- Floating particles -->
    <div class="particles">
      <span v-for="n in 20" :key="n" class="particle" :style="particleStyle(n)"></span>
    </div>

    <!-- Main card -->
    <div class="login-card anim-fade-in-scale">
      <!-- Logo / Brand -->
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="12" fill="url(#logo-grad)"/>
            <path d="M12 28V14l8 8 8-8v14" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            <defs>
              <linearGradient id="logo-grad" x1="0" y1="0" x2="40" y2="40">
                <stop stop-color="#6366F1"/><stop offset="1" stop-color="#8B5CF6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1>混合推荐系统</h1>
        <p>冷启动音乐与视频智能推荐平台</p>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleLogin" class="login-form">
        <!-- Username / Email -->
        <div class="field-group">
          <label>用户名或邮箱</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="7" r="3.5" stroke="currentColor" stroke-width="1.5"/>
              <path d="M4 17c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input
              v-model="username"
              type="text"
              placeholder="请输入用户名或邮箱"
              autocomplete="username"
              required
            />
          </div>
        </div>

        <!-- Password -->
        <div class="field-group">
          <label>密码</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="8" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="10" cy="13" r="1.2" fill="currentColor"/>
              <path d="M10 13.5v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              <path d="M6 8V6a4 4 0 117.5-1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input
              v-model="password"
              :type="showPwd ? 'text' : 'password'"
              placeholder="请输入密码"
              autocomplete="current-password"
              required
            />
            <button type="button" class="toggle-pwd" @click="showPwd = !showPwd" tabindex="-1">
              <svg v-if="!showPwd" viewBox="0 0 20 20" fill="none">
                <path d="M2 10s3-6 8-6 8 6 8 6-3 6-8 6-8-6-8-6z" stroke="currentColor" stroke-width="1.5"/>
                <circle cx="10" cy="10" r="2.5" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              <svg v-else viewBox="0 0 20 20" fill="none">
                <path d="M2 10s3-6 8-6 8 6 8 6-3 6-8 6-8-6-8-6z" stroke="currentColor" stroke-width="1.5"/>
                <path d="M4 4l12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Row: Remember + Forgot -->
        <div class="form-row">
          <label class="checkbox-label">
            <input v-model="rememberMe" type="checkbox" />
            <span class="checkmark"></span>
            记住我
          </label>
        </div>

        <!-- Submit -->
        <button type="submit" :disabled="isLoading" class="btn-submit">
          <span v-if="isLoading" class="spinner"></span>
          <span>{{ isLoading ? '登录中...' : '登 录' }}</span>
        </button>
      </form>

      <!-- Error toast -->
      <transition name="alert">
        <div v-if="error" class="alert-error">
          <svg viewBox="0 0 20 20" fill="currentColor" class="alert-icon">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9a1 1 0 012 0v3a1 1 0 01-2 0V9zm1 6a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
          </svg>
          {{ error }}
        </div>
      </transition>

      <!-- Footer link -->
      <div class="card-footer">
        <span>还没有账号？</span>
        <router-link to="/register">立即注册 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const username = ref("");
const password = ref("");
const showPwd = ref(false);
const rememberMe = ref(false);
const isLoading = ref(false);
const error = ref("");

function particleStyle(n) {
  const left = (n * 37 + 13) % 100;
  const size = 2 + (n % 4);
  const dur = 8 + (n % 10);
  const delay = (n * 1.7) % 8;
  const opacity = 0.15 + (n % 5) * 0.08;
  return {
    left: `${left}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDuration: `${dur}s`,
    animationDelay: `${delay}s`,
    opacity,
    bottom: `${-10 - (n % 6) * 15}px`,
  };
}

async function handleLogin() {
  isLoading.value = true;
  error.value = "";

  try {
    const success = await authStore.login(username.value, password.value);
    if (success) {
      router.push("/dashboard");
    } else {
      error.value = "登录失败，请检查用户名和密码";
    }
  } catch (err) {
    error.value = err.response?.data?.error || "登录失败，请稍后重试";
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
/* ═══════ Full-page background ═══════ */
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #080C1A;
  overflow: hidden;
}

/* ── Animated gradient orbs ── */
.bg-orbs { position: absolute; inset: 0; pointer-events: none; }
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  animation: float-slow 12s ease-in-out infinite;
}
.orb-1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(99,102,241,0.25), transparent);
  top: -15%; left: -10%;
  animation-delay: 0s;
}
.orb-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(139,92,246,0.2), transparent);
  bottom: -20%; right: -8%;
  animation-delay: -5s;
}
.orb-3 {
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(59,130,246,0.18), transparent);
  top: 50%; left: 55%;
  animation-delay: -3s;
}
.orb-4 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(16,185,129,0.1), transparent);
  top: 30%; left: -5%;
  animation-delay: -8s;
}

/* ── Particles ── */
.particles { position: absolute; inset: 0; pointer-events: none; }
.particle {
  position: absolute;
  background: rgba(255,255,255,0.5);
  border-radius: 50%;
  animation: rise linear infinite;
}
@keyframes rise {
  0%   { transform: translateY(0) scale(1); opacity: 0; }
  10%  { opacity: 1; }
  90%  { opacity: 1; }
  100% { transform: translateY(-110vh) scale(0); opacity: 0; }
}

/* ═══════ Card ═══════ */
.login-card {
  position: relative;
  z-index: 1;
  width: 420px;
  max-width: 92vw;
  padding: 44px 40px 36px;
  background: rgba(15, 18, 35, 0.75);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 24px;
  box-shadow:
    0 4px 40px rgba(0,0,0,0.5),
    0 0 0 1px rgba(255,255,255,0.05) inset;
}

/* ── Brand ── */
.brand { text-align: center; margin-bottom: 36px; }
.brand-icon {
  width: 56px; height: 56px;
  margin: 0 auto 16px;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(99,102,241,0.3);
}
.brand-icon svg { width: 100%; height: 100%; display: block; }
.brand h1 {
  font-size: 22px; font-weight: 700; color: #EDF0FC;
  letter-spacing: 0.02em; margin-bottom: 4px;
}
.brand p {
  font-size: 13px; color: #8B90A8; letter-spacing: 0.01em;
}

/* ── Form ── */
.login-form { display: flex; flex-direction: column; gap: 20px; }

.field-group { display: flex; flex-direction: column; gap: 6px; }
.field-group label {
  font-size: 13px; font-weight: 500; color: #B0B5CC; letter-spacing: 0.01em;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute; left: 14px; width: 18px; height: 18px;
  color: #6B7090; pointer-events: none; transition: color 0.2s;
}
.input-wrapper:focus-within .input-icon {
  color: #818CF8;
}
.input-wrapper input {
  width: 100%;
  padding: 11px 14px 11px 42px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: #EDF0FC;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
.input-wrapper input::placeholder { color: #5B6080; }
.input-wrapper input:focus {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.2);
  background: rgba(255,255,255,0.06);
}

.toggle-pwd {
  position: absolute; right: 10px;
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; color: #6B7090;
  cursor: pointer; border-radius: 6px; transition: color 0.2s;
}
.toggle-pwd:hover { color: #B0B5CC; }
.toggle-pwd svg { width: 18px; height: 18px; }

/* ── Row ── */
.form-row {
  display: flex; align-items: center; justify-content: flex-start;
}

/* ── Custom checkbox ── */
.checkbox-label {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: #8B90A8; cursor: pointer; user-select: none;
}
.checkbox-label input { display: none; }
.checkmark {
  width: 18px; height: 18px;
  border: 1.5px solid rgba(255,255,255,0.2);
  border-radius: 5px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.checkbox-label input:checked + .checkmark {
  background: #6366F1; border-color: #6366F1;
}
.checkbox-label input:checked + .checkmark::after {
  content: "";
  width: 5px; height: 9px;
  border: solid #fff; border-width: 0 2px 2px 0;
  transform: rotate(45deg) translateY(-1px);
}

/* ── Submit button ── */
.btn-submit {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  width: 100%; padding: 13px;
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  border: none; border-radius: 10px;
  color: #fff; font-size: 15px; font-weight: 600;
  font-family: inherit; letter-spacing: 0.04em;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(99,102,241,0.35);
  transition: all 0.25s cubic-bezier(0.19,1,0.22,1);
  margin-top: 4px;
}
.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(99,102,241,0.5);
}
.btn-submit:active:not(:disabled) { transform: translateY(0); }
.btn-submit:disabled { opacity: 0.55; cursor: not-allowed; }

/* ── Spinner ── */
.spinner {
  width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin-slow 0.7s linear infinite;
}

/* ── Error alert ── */
.alert-error {
  display: flex; align-items: center; gap: 8px;
  margin-top: 16px; padding: 12px 14px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.25);
  border-radius: 10px;
  color: #FCA5A5; font-size: 13px;
}
.alert-icon { width: 18px; height: 18px; flex-shrink: 0; color: #F87171; }
.alert-enter-active { animation: fadeInDown 0.3s ease; }
.alert-leave-active { animation: fadeInDown 0.2s ease reverse; }

/* ── Footer ── */
.card-footer {
  margin-top: 28px; padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.06);
  text-align: center; font-size: 13px; color: #8B90A8;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.card-footer a {
  color: #818CF8; text-decoration: none; font-weight: 500;
  transition: color 0.2s;
}
.card-footer a:hover { color: #A5B4FC; }
</style>

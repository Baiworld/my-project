<template>
  <div class="register-page">
    <!-- Animated background orbs -->
    <div class="bg-orbs">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>

    <!-- Particles -->
    <div class="particles">
      <span v-for="n in 20" :key="n" class="particle" :style="particleStyle(n)"></span>
    </div>

    <!-- Card -->
    <div class="register-card anim-fade-in-scale">
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="12" fill="url(#reg-grad)"/>
            <path d="M20 12v16m-8-8h16" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
            <defs>
              <linearGradient id="reg-grad" x1="0" y1="0" x2="40" y2="40">
                <stop stop-color="#E8784A"/><stop offset="1" stop-color="#F0A080"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1>创建账户</h1>
        <p>加入基于 Spark 大数据的用户行为实时分析与混合推荐系统，发现属于你的内容</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <!-- Username -->
        <div class="field-group">
          <label>用户名</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="7" r="3.5" stroke="currentColor" stroke-width="1.5"/>
              <path d="M4 17c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input v-model="username" type="text" placeholder="请输入用户名" autocomplete="username" required />
          </div>
        </div>

        <!-- Email -->
        <div class="field-group">
          <label>邮箱</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="4" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <path d="M2 6l8 5 8-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <input v-model="email" type="email" placeholder="请输入邮箱地址" autocomplete="email" required />
          </div>
        </div>

        <!-- Password -->
        <div class="field-group">
          <label>密码</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="8" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="10" cy="13" r="1.2" fill="currentColor"/>
              <path d="M6 8V6a4 4 0 117.5-1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <input v-model="password" :type="showPwd ? 'text' : 'password'" placeholder="请输入密码" autocomplete="new-password" required />
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
          <!-- Strength bar -->
          <div v-if="password" class="strength-bar">
            <div class="strength-segments">
              <span v-for="i in 4" :key="i" :class="['seg', `s${i}`, { active: i <= pwdStrength }]"></span>
            </div>
            <span class="strength-label">{{ strengthLabel }}</span>
          </div>
        </div>

        <!-- Confirm Password -->
        <div class="field-group">
          <label>确认密码</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 20 20" fill="none">
              <path d="M5 10l3.5 3.5L15 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <input
              v-model="confirmPassword"
              :type="showPwd ? 'text' : 'password'"
              placeholder="请再次输入密码"
              autocomplete="new-password"
              required
              :class="{ 'input-error': confirmPassword && password !== confirmPassword }"
            />
          </div>
        </div>

        <!-- Submit -->
        <button type="submit" :disabled="isLoading || !isFormValid" class="btn-submit">
          <span v-if="isLoading" class="spinner"></span>
          <span>{{ isLoading ? '注册中...' : '注 册' }}</span>
        </button>
      </form>

      <!-- Alerts -->
      <transition name="alert">
        <div v-if="error" class="alert-error">
          <svg viewBox="0 0 20 20" fill="currentColor" class="alert-icon"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9a1 1 0 012 0v3a1 1 0 01-2 0V9zm1 6a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/></svg>
          {{ error }}
        </div>
      </transition>
      <transition name="alert">
        <div v-if="confirmPassword && password !== confirmPassword" class="alert-warn">
          <svg viewBox="0 0 20 20" fill="currentColor" class="alert-icon"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v4a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
          两次输入的密码不一致
        </div>
      </transition>

      <div class="card-footer">
        <span>已有账号？</span>
        <router-link to="/login">立即登录 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const username = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const showPwd = ref(false);
const isLoading = ref(false);
const error = ref("");

const pwdStrength = computed(() => {
  const p = password.value;
  if (!p) return 0;
  let score = 0;
  if (p.length >= 8) score++;
  if (p.length >= 12) score++;
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score++;
  if (/\d/.test(p)) score++;
  if (/[^a-zA-Z0-9]/.test(p)) score++;
  return Math.min(4, score);
});

const strengthLabel = computed(() => {
  const labels = ["", "弱", "一般", "较强", "强"];
  return labels[pwdStrength.value] || "";
});

const isFormValid = computed(() => {
  return username.value && email.value && password.value && confirmPassword.value
    && password.value === confirmPassword.value
    && password.value.length >= 8;
});

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

async function handleRegister() {
  if (password.value !== confirmPassword.value) {
    error.value = "两次输入的密码不一致";
    return;
  }
  isLoading.value = true;
  error.value = "";

  try {
    const success = await authStore.register(username.value, email.value, password.value, confirmPassword.value);
    if (success) {
      router.push("/login");
    } else {
      error.value = "注册失败，请稍后重试";
    }
  } catch (err) {
    error.value = err.response?.data?.error || "注册失败，请稍后重试";
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
/* ═══════ Full-page ═══════ */
.register-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-root);
  overflow: hidden;
}

/* ── Orbs ── */
.bg-orbs { position: absolute; inset: 0; pointer-events: none; }
.orb {
  position: absolute; border-radius: 50%; filter: blur(100px);
  animation: float-slow 12s ease-in-out infinite;
}
.orb-1 { width:500px; height:500px; background:radial-gradient(circle,rgba(232,120,74,0.2),transparent); top:-15%; left:-10%; animation-delay:0s; }
.orb-2 { width:400px; height:400px; background:radial-gradient(circle,rgba(240,160,128,0.18),transparent); bottom:-20%; right:-8%; animation-delay:-5s; }
.orb-3 { width:350px; height:350px; background:radial-gradient(circle,rgba(232,160,64,0.15),transparent); top:50%; left:55%; animation-delay:-3s; }
.orb-4 { width:300px; height:300px; background:radial-gradient(circle,rgba(45,157,122,0.1),transparent); top:30%; left:-5%; animation-delay:-8s; }

/* ── Particles ── */
.particles { position: absolute; inset:0; pointer-events:none; }
.particle {
  position:absolute; background:rgba(232,120,74,0.4);
  border-radius:50%; animation:rise linear infinite;
}

/* ═══════ Card ═══════ */
.register-card {
  position: relative; z-index: 1;
  width: 440px; max-width: 92vw;
  padding: 40px 40px 32px;
  background: rgba(255,255,255,0.85);
  -webkit-backdrop-filter: blur(40px);
  backdrop-filter: blur(40px);
  border: 1px solid var(--border-default);
  border-radius: 24px;
  box-shadow: 0 4px 40px rgba(120,80,50,0.15), 0 0 0 1px rgba(255,255,255,0.8) inset;
}

/* ── Brand ── */
.brand { text-align:center; margin-bottom:28px; }
.brand-icon { width:52px; height:52px; margin:0 auto 14px; border-radius:14px; box-shadow:0 8px 24px rgba(232,120,74,0.3); }
.brand-icon svg { width:100%; height:100%; display:block; }
.brand h1 { font-size:22px; font-weight:700; color:var(--text-primary); letter-spacing:0.02em; margin-bottom:4px; }
.brand p { font-size:13px; color:var(--text-secondary); }

/* ── Form ── */
.register-form { display:flex; flex-direction:column; gap:16px; }

.field-group { display:flex; flex-direction:column; gap:6px; }
.field-group label { font-size:13px; font-weight:500; color:var(--text-secondary); }

.input-wrapper { position:relative; display:flex; align-items:center; }
.input-icon { position:absolute; left:14px; width:18px; height:18px; color:var(--text-tertiary); pointer-events:none; transition:color 0.2s; }
.input-wrapper:focus-within .input-icon { color:var(--color-primary); }
.input-wrapper input {
  width:100%; padding:11px 14px 11px 42px;
  background:rgba(180,130,100,0.04);
  border:1px solid var(--border-default);
  border-radius:10px; color:var(--text-primary); font-size:14px; font-family:inherit;
  outline:none; transition:border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
.input-wrapper input::placeholder { color:var(--text-tertiary); }
.input-wrapper input:focus {
  border-color:var(--color-primary);
  box-shadow:0 0 0 3px var(--color-primary-glow);
  background:rgba(180,130,100,0.06);
}
.input-wrapper .input-error { border-color:#EF4444; box-shadow:0 0 0 3px rgba(239,68,68,0.15); }

.toggle-pwd {
  position:absolute; right:10px; width:32px; height:32px;
  display:flex; align-items:center; justify-content:center;
  background:none; border:none; color:var(--text-tertiary); cursor:pointer;
  border-radius:6px; transition:color 0.2s;
}
.toggle-pwd:hover { color:var(--text-secondary); }
.toggle-pwd svg { width:18px; height:18px; }

/* ── Strength bar ── */
.strength-bar { display:flex; align-items:center; gap:10px; margin-top:4px; }
.strength-segments { display:flex; gap:4px; flex:1; }
.seg { height:3px; flex:1; border-radius:2px; background:rgba(180,130,100,0.08); transition:background 0.3s; }
.seg.s1.active { background:#EF4444; }
.seg.s2.active { background:#F59E0B; }
.seg.s3.active { background:#3B82F6; }
.seg.s4.active { background:#10B981; }
.strength-label { font-size:11px; color:var(--text-secondary); min-width:24px; }

/* ── Button ── */
.btn-submit {
  display:flex; align-items:center; justify-content:center; gap:10px;
  width:100%; padding:13px;
  background:linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border:none; border-radius:10px;
  color:#fff; font-size:15px; font-weight:600; font-family:inherit;
  letter-spacing:0.04em; cursor:pointer;
  box-shadow:0 4px 16px rgba(232,120,74,0.3);
  transition:all 0.25s cubic-bezier(0.19,1,0.22,1);
  margin-top:4px;
}
.btn-submit:hover:not(:disabled) { transform:translateY(-1px); box-shadow:0 6px 24px var(--color-primary-glow); }
.btn-submit:active:not(:disabled) { transform:translateY(0); }
.btn-submit:disabled { opacity:0.5; cursor:not-allowed; }

/* ── Spinner ── */
.spinner { width:18px; height:18px; border:2px solid rgba(255,255,255,0.3); border-top-color:#fff; border-radius:50%; animation:spin-slow 0.7s linear infinite; }

/* ── Alerts ── */
.alert-error, .alert-warn {
  display:flex; align-items:center; gap:8px;
  margin-top:12px; padding:12px 14px;
  border-radius:10px; font-size:13px;
}
.alert-error { background:rgba(224,85,74,0.08); border:1px solid rgba(224,85,74,0.2); color:#D0554A; }
.alert-warn  { background:rgba(232,160,64,0.08); border:1px solid rgba(232,160,64,0.2); color:#C88030; }
.alert-icon { width:18px; height:18px; flex-shrink:0; }
.alert-error .alert-icon { color:#E0554A; }
.alert-warn  .alert-icon { color:#E8A040; }
.alert-enter-active { animation:fadeInDown 0.3s ease; }
.alert-leave-active { animation:fadeInDown 0.2s ease reverse; }

/* ── Footer ── */
.card-footer {
  margin-top:24px; padding-top:18px;
  border-top:1px solid rgba(180,130,100,0.06);
  text-align:center; font-size:13px; color:var(--text-secondary);
  display:flex; align-items:center; justify-content:center; gap:6px;
}
.card-footer a { color:#34D399; text-decoration:none; font-weight:500; transition:color 0.2s; }
.card-footer a:hover { color:#6EE7B7; }
</style>


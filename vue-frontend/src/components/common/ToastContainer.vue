<template>
  <teleport to="body">
    <div class="toast-stack" aria-live="polite">
      <transition-group name="toast">
        <div
          v-for="t in toastStore.toasts"
          :key="t.id"
          :class="['toast-item', `toast-${t.type}`, { 'toast-leaving': t.leaving }]"
        >
          <span class="toast-icon" v-html="iconFor(t.type)"></span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" @click="toastStore.remove(t.id)" title="关闭">&times;</button>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import { useToastStore } from "@/stores/toast";

const toastStore = useToastStore();

const icons = {
  success: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 10l3 3 7-7"/></svg>',
  error: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="7"/><path d="M7 7l6 6M13 7l-6 6"/></svg>',
  warning: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3L2 18h16L10 3zM10 8v4M10 14v1"/></svg>',
  info: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="7"/><path d="M10 9v5M10 6.5v1"/></svg>',
};

function iconFor(type) {
  return icons[type] || icons.info;
}
</script>

<style scoped>
.toast-stack {
  position: fixed; top: 20px; right: 20px; z-index: 10000;
  display: flex; flex-direction: column; gap: 10px;
  pointer-events: none; max-width: 380px;
}

.toast-item {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px rgba(120,80,50,0.12);
  pointer-events: auto;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: all 0.25s var(--ease-out-expo);
}

.toast-item.toast-leaving {
  opacity: 0;
  transform: translateX(40px);
}

.toast-success { border-left: 3px solid var(--color-teal); }
.toast-error   { border-left: 3px solid var(--color-danger); }
.toast-warning { border-left: 3px solid var(--color-amber); }
.toast-info    { border-left: 3px solid var(--color-sky); }

.toast-icon {
  width: 20px; height: 20px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.toast-success .toast-icon { color: var(--color-teal); }
.toast-error   .toast-icon { color: var(--color-danger); }
.toast-warning .toast-icon { color: var(--color-amber); }
.toast-info    .toast-icon { color: var(--color-sky); }

.toast-icon :deep(svg) { width: 18px; height: 18px; }

.toast-msg { flex: 1; line-height: 1.4; }

.toast-close {
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none;
  color: var(--text-tertiary); font-size: 18px; cursor: pointer;
  border-radius: 6px; flex-shrink: 0;
  transition: all var(--duration-fast);
}
.toast-close:hover { background: rgba(180,130,100,0.08); color: var(--text-primary); }

/* transition-group */
.toast-enter-active { transition: all 0.3s var(--ease-out-back); }
.toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from { opacity: 0; transform: translateX(60px); }
.toast-leave-to   { opacity: 0; transform: translateX(40px); }
</style>

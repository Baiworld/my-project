<template>
  <teleport to="body">
    <transition name="modal">
      <div v-if="confirmStore.visible" class="confirm-overlay" @click.self="confirmStore.cancel">
        <div class="confirm-card anim-fade-in-scale">
          <div class="confirm-icon" :class="`icon-${confirmStore.variant}`">
            <svg v-if="confirmStore.variant === 'danger'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
            <svg v-else-if="confirmStore.variant === 'warning'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 22h20L12 2zM12 9v5M12 17v1"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
          </div>
          <h3 class="confirm-title">{{ confirmStore.title }}</h3>
          <p class="confirm-message">{{ confirmStore.message }}</p>
          <div class="confirm-actions">
            <button @click="confirmStore.cancel" class="btn btn-ghost">{{ confirmStore.cancelText }}</button>
            <button @click="confirmStore.confirm" :class="['btn', actionBtnClass]">{{ confirmStore.confirmText }}</button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { computed } from "vue";
import { useConfirmStore } from "@/stores/confirm";

const confirmStore = useConfirmStore();

const actionBtnClass = computed(() => {
  const map = { danger: "btn-danger", warning: "btn-amber", info: "btn-primary" };
  return map[confirmStore.variant] || "btn-primary";
});
</script>

<style scoped>
.confirm-overlay {
  position: fixed; inset: 0; z-index: 9000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(40,20,10,0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.confirm-card {
  width: 400px; max-width: 90vw;
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  box-shadow: 0 16px 48px rgba(120,80,50,0.18);
  padding: 32px 28px 24px;
  text-align: center;
}

.confirm-icon {
  width: 52px; height: 52px; margin: 0 auto 16px;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
}
.confirm-icon :deep(svg) { width: 26px; height: 26px; }
.icon-danger  { background: rgba(240,98,110,0.12);  color: var(--color-rose-dark); }
.icon-warning { background: rgba(245,158,11,0.12); color: var(--color-amber-dark); }
.icon-info    { background: rgba(91,155,213,0.12);  color: var(--color-sky); }

.confirm-title {
  font-size: var(--font-size-lg); font-weight: 700;
  color: var(--text-primary); margin-bottom: 8px;
}

.confirm-message {
  font-size: var(--font-size-sm); color: var(--text-secondary);
  line-height: 1.6; margin-bottom: 24px;
}

.confirm-actions {
  display: flex; gap: 10px; justify-content: center;
}

/* modal transition reuse */
.modal-enter-active { transition: opacity 0.25s ease; }
.modal-enter-active .confirm-card { animation: fadeInScale 0.3s cubic-bezier(0.19,1,0.22,1); }
.modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>

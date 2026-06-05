<template>
  <div :class="['metric-card', `accent-${accent}`]">
    <!-- Glow border -->
    <div class="card-glow"></div>

    <div class="card-inner">
      <!-- Icon -->
      <div class="card-icon">
        <slot name="icon">
          <svg v-if="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path v-for="d in iconPaths[icon]" :key="d" :d="d" />
          </svg>
        </slot>
      </div>

      <!-- Content -->
      <div class="card-body">
        <p class="card-title">{{ title }}</p>
        <div class="card-value-row">
          <span class="card-value" ref="valueEl">{{ displayValue }}</span>
          <span v-if="unit" class="card-unit">{{ unit }}</span>
        </div>
      </div>

      <!-- Trend -->
      <div v-if="trend" :class="['card-trend', trendType]">
        <svg viewBox="0 0 16 16" fill="currentColor" class="trend-arrow">
          <path v-if="trendType === 'up'" d="M8 3l5 6H3z"/>
          <path v-else d="M8 13l5-6H3z"/>
        </svg>
        <span>{{ trend }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: "" },
  trend: { type: String, default: "" },
  trendType: { type: String, default: "up", validator: (v) => ["up", "down"].includes(v) },
  accent: { type: String, default: "blue", validator: (v) => ["blue","green","purple","orange"].includes(v) },
  icon: { type: String, default: "" },
});

const displayValue = computed(() => {
  const v = props.value;
  if (typeof v === "number") return v.toLocaleString();
  return v;
});

const iconPaths = {
  users: ["M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2", "M23 21v-2a4 4 0 00-3-3.87", "M16 3.13a4 4 0 010 7.75"],
  target: ["M12 2a10 10 0 100 20 10 10 0 000-20z", "M12 6v6l4 2"],
  trend: ["M22 12h-4l-3 9L9 3l-3 9H2"],
  clock: ["M12 2a10 10 0 100 20 10 10 0 000-20z", "M12 6v6l4 2"],
};
</script>

<style scoped>
.metric-card {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  overflow: hidden;
  transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
}
.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* ── Glow accent ── */
.card-glow {
  position: absolute;
  top: -50%;
  right: -30%;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  opacity: 0.12;
  transition: opacity 0.3s ease;
  pointer-events: none;
}
.metric-card:hover .card-glow { opacity: 0.22; }

.accent-blue   .card-glow { background: radial-gradient(circle, #6366F1, transparent); }
.accent-green  .card-glow { background: radial-gradient(circle, #10B981, transparent); }
.accent-purple .card-glow { background: radial-gradient(circle, #8B5CF6, transparent); }
.accent-orange .card-glow { background: radial-gradient(circle, #F59E0B, transparent); }

/* ── Inner layout ── */
.card-inner {
  position: relative; z-index: 1;
  display: flex; align-items: flex-start; gap: 16px;
}

/* ── Icon ── */
.card-icon {
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 12px;
  flex-shrink: 0;
}
.card-icon svg { width: 22px; height: 22px; }

.accent-blue   .card-icon { background: rgba(99,102,241,0.15);  color: #818CF8; }
.accent-green  .card-icon { background: rgba(16,185,129,0.15);  color: #34D399; }
.accent-purple .card-icon { background: rgba(139,92,246,0.15);  color: #A78BFA; }
.accent-orange .card-icon { background: rgba(245,158,11,0.15);  color: #FBBF24; }

/* ── Body ── */
.card-body { flex: 1; min-width: 0; }
.card-title {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}
.card-value-row { display: flex; align-items: baseline; gap: 4px; }
.card-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.card-unit {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

/* ── Trend badge ── */
.card-trend {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  flex-shrink: 0;
  align-self: center;
}
.card-trend.up   { background: rgba(16,185,129,0.12); color: #34D399; }
.card-trend.down { background: rgba(239,68,68,0.12);  color: #F87171; }
.trend-arrow { width: 12px; height: 12px; }
</style>

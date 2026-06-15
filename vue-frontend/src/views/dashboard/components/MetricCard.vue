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
  accent: { type: String, default: "coral", validator: (v) => ["coral","amber","teal","indigo","rose","gold","sky","blue","green","purple","orange"].includes(v) },
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
  background: linear-gradient(180deg, var(--bg-surface), var(--bg-surface-warm));
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  padding: 22px 24px;
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-out-expo);
}
.metric-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.accent-coral::before  { background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light)); }
.accent-amber::before  { background: linear-gradient(90deg, var(--color-amber), var(--color-amber-light)); }
.accent-teal::before   { background: linear-gradient(90deg, var(--color-teal), var(--color-teal-light)); }
.accent-indigo::before { background: linear-gradient(90deg, var(--color-indigo), var(--color-indigo-light)); }
.accent-rose::before   { background: linear-gradient(90deg, var(--color-rose), var(--color-rose-light)); }
.accent-gold::before   { background: linear-gradient(90deg, var(--color-gold), var(--color-gold-light)); }
.accent-sky::before    { background: linear-gradient(90deg, var(--color-sky), var(--color-sky-light)); }
.accent-blue::before   { background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light)); }
.accent-green::before  { background: linear-gradient(90deg, var(--color-teal), var(--color-teal-light)); }
.accent-purple::before { background: linear-gradient(90deg, var(--color-plum), var(--color-plum-light)); }
.accent-orange::before { background: linear-gradient(90deg, var(--color-gold), var(--color-gold-light)); }

.metric-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  border-color: var(--border-strong);
}

/* ── Glow accent ── */
.card-glow {
  position: absolute;
  top: -40%; right: -20%;
  width: 140px; height: 140px;
  border-radius: 50%; opacity: 0.1;
  transition: opacity 0.3s ease;
  pointer-events: none;
}
.metric-card:hover .card-glow { opacity: 0.2; }

.accent-coral .card-glow  { background: radial-gradient(circle, var(--color-primary), transparent); }
.accent-amber .card-glow  { background: radial-gradient(circle, var(--color-amber), transparent); }
.accent-teal .card-glow   { background: radial-gradient(circle, var(--color-teal), transparent); }
.accent-indigo .card-glow { background: radial-gradient(circle, var(--color-indigo), transparent); }
.accent-rose .card-glow   { background: radial-gradient(circle, var(--color-rose), transparent); }
.accent-gold .card-glow   { background: radial-gradient(circle, var(--color-gold), transparent); }
.accent-sky .card-glow    { background: radial-gradient(circle, var(--color-sky), transparent); }
.accent-blue .card-glow   { background: radial-gradient(circle, var(--color-primary), transparent); }
.accent-green .card-glow  { background: radial-gradient(circle, var(--color-teal), transparent); }
.accent-purple .card-glow { background: radial-gradient(circle, var(--color-plum), transparent); }
.accent-orange .card-glow { background: radial-gradient(circle, var(--color-gold), transparent); }

/* ── Inner layout ── */
.card-inner { position: relative; z-index: 1; display: flex; align-items: flex-start; gap: 16px; }

/* ── Icon ── */
.card-icon {
  width: 46px; height: 46px; display: flex; align-items: center; justify-content: center;
  border-radius: 12px; flex-shrink: 0;
}
.card-icon svg { width: 22px; height: 22px; }

.accent-coral .card-icon  { background: linear-gradient(135deg, rgba(232,120,74,0.15), rgba(240,160,128,0.08)); color: var(--color-primary-dark); }
.accent-amber .card-icon  { background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(252,211,77,0.08)); color: var(--color-amber-dark); }
.accent-teal .card-icon   { background: linear-gradient(135deg, rgba(45,157,122,0.15), rgba(91,200,168,0.08)); color: var(--color-teal); }
.accent-indigo .card-icon { background: linear-gradient(135deg, rgba(124,111,223,0.15), rgba(168,156,240,0.08)); color: var(--color-indigo); }
.accent-rose .card-icon   { background: linear-gradient(135deg, rgba(240,98,110,0.15), rgba(248,160,168,0.08)); color: var(--color-rose-dark); }
.accent-gold .card-icon   { background: linear-gradient(135deg, rgba(232,160,64,0.15), rgba(240,200,120,0.08)); color: var(--color-gold-dark); }
.accent-sky .card-icon    { background: linear-gradient(135deg, rgba(91,155,213,0.15), rgba(139,192,240,0.08)); color: #4A8AC5; }
.accent-blue .card-icon   { background: linear-gradient(135deg, rgba(232,120,74,0.15), rgba(240,160,128,0.08)); color: var(--color-primary-dark); }
.accent-green .card-icon  { background: linear-gradient(135deg, rgba(45,157,122,0.15), rgba(91,200,168,0.08)); color: var(--color-teal); }
.accent-purple .card-icon { background: linear-gradient(135deg, rgba(168,122,184,0.15), rgba(208,168,216,0.08)); color: #8A64B4; }
.accent-orange .card-icon { background: linear-gradient(135deg, rgba(232,160,64,0.15), rgba(240,200,120,0.08)); color: var(--color-gold-dark); }

/* ── Body ── */
.card-body { flex: 1; min-width: 0; }
.card-title {
  font-size: var(--font-size-xs); color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 8px; font-weight: 600;
}
.card-value-row { display: flex; align-items: baseline; gap: 4px; }
.card-value {
  font-size: var(--font-size-2xl); font-weight: 800;
  color: var(--text-primary); line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.card-unit { font-size: var(--font-size-sm); color: var(--text-tertiary); }

/* ── Trend badge ── */
.card-trend {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 12px; border-radius: 99px;
  font-size: var(--font-size-xs); font-weight: 600;
  flex-shrink: 0; align-self: center;
}
.card-trend.up   { background: linear-gradient(135deg, rgba(45,157,122,0.15), rgba(91,200,168,0.08)); color: #2D9D7A; }
.card-trend.down { background: linear-gradient(135deg, rgba(240,98,110,0.15), rgba(248,160,168,0.08)); color: #E0554A; }
.trend-arrow { width: 12px; height: 12px; }
</style>

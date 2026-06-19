<template>
  <span class="anim-num">{{ displayValue }}</span>
</template>

<script setup>
import { ref, watch, onUnmounted } from "vue";

const props = defineProps({
  value: { type: [Number, String], default: 0 },
  duration: { type: Number, default: 600 },
  decimals: { type: Number, default: -1 },
});

const displayValue = ref(formatValue(toNum(props.value)));

function toNum(v) {
  if (typeof v === "string") return parseFloat(v) || 0;
  return v;
}

function formatValue(v) {
  if (props.decimals >= 0) return v.toFixed(props.decimals);
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(2);
}

let raf = null;

function animate(from, to) {
  if (raf) cancelAnimationFrame(raf);
  const start = performance.now();

  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / props.duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    const current = from + (to - from) * eased;
    displayValue.value = formatValue(current);
    if (progress < 1) {
      raf = requestAnimationFrame(step);
    } else {
      displayValue.value = formatValue(to);
    }
  }
  raf = requestAnimationFrame(step);
}

watch(
  () => props.value,
  (newVal, oldVal) => {
    const n = toNum(newVal);
    const o = toNum(oldVal);
    if (n !== o) animate(o, n);
  },
  { immediate: false }
);

onUnmounted(() => {
  if (raf) cancelAnimationFrame(raf);
});
</script>

<style scoped>
.anim-num { font-variant-numeric: tabular-nums; }
</style>

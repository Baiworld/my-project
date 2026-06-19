<template>
  <div class="skeleton-table surface-card" :style="{ padding: '16px' }">
    <div class="sk-header">
      <div v-for="i in cols" :key="'h'+i" class="sk-cell sk-h" :style="{ width: randomWidth(i) }"></div>
    </div>
    <div v-for="r in rows" :key="'r'+r" class="sk-header sk-body-row">
      <div v-for="i in cols" :key="'b'+r+'-'+i" class="sk-cell sk-b" :style="{ width: randomWidth(i + r * 10) }"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  rows: { type: Number, default: 5 },
  cols: { type: Number, default: 5 },
});

const widths = ["20%", "28%", "14%", "18%", "20%"];
function randomWidth(i) { return widths[i % widths.length]; }
</script>

<style scoped>
.skeleton-table { overflow: hidden; border-radius: var(--radius-xl); }
.sk-header { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border-subtle); }
.sk-body-row { border-bottom: 1px solid var(--border-subtle); padding: 10px 0; }
.sk-cell { height: 14px; border-radius: 4px; background: linear-gradient(90deg, rgba(180,130,100,0.06), rgba(180,130,100,0.14), rgba(180,130,100,0.06)); background-size: 200% 100%; animation: shimmer 1.6s infinite; }
.sk-h { height: 11px; background: linear-gradient(90deg, rgba(180,130,100,0.1), rgba(180,130,100,0.18), rgba(180,130,100,0.1)); background-size: 200% 100%; animation: shimmer 1.6s infinite; }
</style>

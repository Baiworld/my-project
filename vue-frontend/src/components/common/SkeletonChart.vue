<template>
  <div class="skeleton-chart chart-panel">
    <div class="sk-bar"></div>
  </div>
</template>

<style scoped>
.skeleton-chart { min-height: 280px; display: flex; align-items: center; justify-content: center; }
.sk-bar {
  width: 75%; height: 160px; border-radius: var(--radius-md);
  background: linear-gradient(90deg, rgba(180,130,100,0.06), rgba(180,130,100,0.14), rgba(180,130,100,0.06));
  background-size: 200% 100%; animation: shimmer 1.6s infinite;
}
</style>

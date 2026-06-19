<template>
  <div class="skeleton-card surface-card">
    <div class="sk-row sk-title"></div>
    <div class="sk-row sk-value"></div>
    <div class="sk-row sk-sub"></div>
  </div>
</template>

<style scoped>
.skeleton-card { padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }
.sk-row { height: 16px; border-radius: 4px; background: linear-gradient(90deg, rgba(180,130,100,0.08), rgba(180,130,100,0.15), rgba(180,130,100,0.08)); background-size: 200% 100%; animation: shimmer 1.6s infinite; }
.sk-title { width: 60%; height: 12px; }
.sk-value { width: 40%; height: 28px; }
.sk-sub { width: 50%; height: 12px; }
</style>

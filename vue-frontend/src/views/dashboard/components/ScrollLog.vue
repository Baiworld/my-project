<template>
  <div class="log-container">
    <div v-if="logs.length === 0" class="log-empty">
      <svg viewBox="0 0 40 40" fill="none" class="empty-graphic"><rect x="6" y="6" width="28" height="28" rx="3" stroke="currentColor" stroke-width="1.2" opacity="0.4"/><path d="M6 14h28" stroke="currentColor" stroke-width="1.2" opacity="0.4"/></svg>
      <p>暂无行为日志</p>
      <span>用户行为将实时显示在此处</span>
    </div>
    <div v-else class="log-list">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="log-entry"
        :style="{ animationDelay: `${index * 0.02}s` }"
      >
        <span class="log-time">{{ log.timestamp || '--:--:--' }}</span>
        <span class="log-user">用户{{ log.user_id }}</span>
        <span :class="['log-event', eventClass(log.event_type)]">{{ log.event_type }}</span>
        <span class="log-type">{{ log.content_type }}</span>
        <span class="log-cid">#{{ log.content_id }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  logs: { type: Array, default: () => [] },
});

function eventClass(type) {
  const map = {
    "播放": "ev-play",
    "点赞": "ev-like",
    "收藏": "ev-bookmark",
    "分享": "ev-share",
    "评论": "ev-comment",
    "跳过": "ev-skip",
    "完播": "ev-complete",
  };
  return map[type] || "";
}
</script>

<style scoped>
.log-container {
  max-height: 220px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}

/* ── Empty state ── */
.log-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 32px 16px; text-align: center;
}
.empty-graphic { width: 40px; height: 40px; color: var(--text-tertiary); margin-bottom: 10px; }
.log-empty p  { color: var(--text-secondary); margin-bottom: 2px; }
.log-empty span { font-size: 11px; color: var(--text-tertiary); }

/* ── Log entries ── */
.log-list {
  display: flex; flex-direction: column;
  padding: 8px 16px 12px;
}
.log-entry {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 10px;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: background var(--duration-fast) ease;
  animation: fadeIn 0.25s ease both;
}
.log-entry:hover { background: rgba(255,255,255,0.03); }

.log-time {
  color: var(--text-tertiary);
  white-space: nowrap;
  min-width: 70px;
}
.log-user {
  color: #818CF8;
  min-width: 60px;
}
.log-event {
  font-weight: 600;
  min-width: 36px;
}
.log-type {
  color: #FBBF24;
}
.log-cid {
  color: var(--text-tertiary);
  margin-left: auto;
}

/* ── Event colors ── */
.ev-play     { color: #34D399; }
.ev-like     { color: #F472B6; }
.ev-bookmark { color: #FBBF24; }
.ev-share    { color: #60A5FA; }
.ev-comment  { color: #A78BFA; }
.ev-skip     { color: #F87171; }
.ev-complete { color: #2DD4BF; }
</style>

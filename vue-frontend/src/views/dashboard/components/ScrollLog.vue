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
        :class="['log-entry', eventClass(log.event_type)]"
        :style="{ animationDelay: `${index * 0.02}s` }"
      >
        <span class="log-time">{{ log.timestamp || '--:--:--' }}</span>
        <span class="log-icon">
          <svg v-if="log.content_type === 'music' || log.content_type === '音乐'" viewBox="0 0 16 16" fill="currentColor"><path d="M6 12V4l8-1.5v8"/><circle cx="4.5" cy="11" r="2"/><circle cx="12" cy="9.5" r="2"/></svg>
          <svg v-else viewBox="0 0 16 16" fill="currentColor"><polygon points="4,1.5 14,8 4,14.5"/></svg>
        </span>
        <span class="log-user" @click.stop="$emit('user-click', log.user_id)">用户{{ log.user_id }}</span>
        <span class="log-action">{{ eventLabel(log.event_type) }}</span>
        <span class="log-target">{{ contentLabel(log) }}</span>
        <span class="log-cid">#{{ log.content_id }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  logs: { type: Array, default: () => [] },
});

defineEmits(["user-click"]);

const EVENT_MAP = {
  "play": { label: "播放了", cls: "ev-play" },
  "播放": { label: "播放了", cls: "ev-play" },
  "like": { label: "点赞了", cls: "ev-like" },
  "点赞": { label: "点赞了", cls: "ev-like" },
  "favorite": { label: "收藏了", cls: "ev-bookmark" },
  "收藏": { label: "收藏了", cls: "ev-bookmark" },
  "share": { label: "分享了", cls: "ev-share" },
  "分享": { label: "分享了", cls: "ev-share" },
  "comment": { label: "评论了", cls: "ev-comment" },
  "评论": { label: "评论了", cls: "ev-comment" },
  "skip": { label: "跳过了", cls: "ev-skip" },
  "跳过": { label: "跳过了", cls: "ev-skip" },
  "complete": { label: "完播了", cls: "ev-complete" },
  "完播": { label: "完播了", cls: "ev-complete" },
};

function eventLabel(type) {
  return EVENT_MAP[type]?.label || type || "操作了";
}

function eventClass(type) {
  return EVENT_MAP[type]?.cls || "";
}

function contentLabel(log) {
  if (log.content_title) {
    const type = log.content_type;
    const icon = (type === "music" || type === "音乐") ? "" : "";
    return `《${log.content_title}》`;
  }
  const type = log.content_type;
  if (type === "music" || type === "音乐") return "一首音乐";
  if (type === "video" || type === "视频") return "一个视频";
  return type || "内容";
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
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: all var(--duration-fast) ease;
  animation: fadeIn 0.25s ease both;
  border-left: 3px solid transparent;
}
.log-entry:hover { background: rgba(180,130,100,0.05); }

.log-entry.ev-play     { border-left-color: #34D399; }
.log-entry.ev-like     { border-left-color: #F472B6; }
.log-entry.ev-bookmark { border-left-color: #FBBF24; }
.log-entry.ev-share    { border-left-color: #60A5FA; }
.log-entry.ev-comment  { border-left-color: #A78BFA; }
.log-entry.ev-skip     { border-left-color: #F87171; }
.log-entry.ev-complete { border-left-color: #2DD4BF; }

.log-time {
  color: var(--text-tertiary);
  white-space: nowrap;
  min-width: 66px;
  font-size: 11px;
}
.log-icon {
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.log-icon svg { width: 14px; height: 14px; }
.ev-play .log-icon, .ev-complete .log-icon { color: #34D399; }
.ev-like .log-icon { color: #F472B6; }
.ev-bookmark .log-icon { color: #FBBF24; }
.ev-share .log-icon { color: #60A5FA; }
.ev-comment .log-icon { color: #A78BFA; }
.ev-skip .log-icon { color: #F87171; }

.log-user { color: var(--color-primary); min-width: 56px; font-weight: 500; cursor: pointer; transition: all var(--duration-fast); }
.log-user:hover { text-decoration: underline; color: var(--color-primary-dark); }
.log-action { font-weight: 600; min-width: 42px; }
.ev-play .log-action     { color: #34D399; }
.ev-like .log-action     { color: #F472B6; }
.ev-bookmark .log-action { color: #FBBF24; }
.ev-share .log-action    { color: #60A5FA; }
.ev-comment .log-action  { color: #A78BFA; }
.ev-skip .log-action     { color: #F87171; }
.ev-complete .log-action { color: #2DD4BF; }

.log-target { color: var(--text-secondary); min-width: 54px; }
.log-cid { color: var(--text-tertiary); margin-left: auto; font-size: 11px; }
</style>


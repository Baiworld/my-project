<template>
  <div class="card-grid-wrap">
    <div v-if="items.length === 0" class="grid-empty">
      <p>暂无推荐内容</p>
      <span>实时推荐数据将显示在此处</span>
    </div>
    <div v-else class="card-grid">
      <div
        v-for="(item, idx) in items"
        :key="item.content_id || idx"
        class="content-card"
        :style="{ animationDelay: `${idx * 0.04}s` }"
        @click="$emit('item-click', item)"
      >
        <div class="card-cover" :class="item.content_type === 'music' ? 'cover-music' : 'cover-video'">
          <svg v-if="item.content_type === 'music'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="cover-icon">
            <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="cover-icon">
            <polygon points="5,3 19,12 5,21"/><rect x="1" y="1" width="22" height="22" rx="3" stroke-width="1" fill="none"/>
          </svg>
          <span class="cover-duration">{{ formatDuration(item.duration) }}</span>
        </div>
        <div class="card-body">
          <h4 class="card-title">{{ item.title || '未知标题' }}</h4>
          <p class="card-artist">{{ item.artist_or_author || '未知艺人' }}</p>
          <div class="card-meta">
            <span :class="['badge', item.content_type === 'music' ? 'badge-indigo' : 'badge-amber']">
              {{ item.content_type === 'music' ? '音乐' : '视频' }}
            </span>
            <span class="card-score" v-if="item.hot_score">
              <svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12"><path d="M8 1l2 5h5l-4 3.5L12.5 15 8 11.5 3.5 15 5 9.5 1 6h5l2-5z"/></svg>
              {{ Number(item.hot_score).toFixed(0) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, default: () => [] },
});

defineEmits(["item-click"]);

function formatDuration(seconds) {
  if (!seconds) return "--:--";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}
</script>

<style scoped>
.card-grid-wrap { min-height: 80px; }

.grid-empty { text-align: center; padding: 40px 16px; }
.grid-empty p { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: 2px; }
.grid-empty span { font-size: 11px; color: var(--text-tertiary); }

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}

.content-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out-expo);
  animation: fadeInUp 0.35s var(--ease-out-expo) both;
}
.content-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  border-color: var(--border-accent);
}

.card-cover {
  height: 100px;
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.cover-music {
  background: linear-gradient(135deg, #7C6FDF 0%, #A89CF0 50%, #C4B5FD 100%);
}
.cover-video {
  background: linear-gradient(135deg, #E8784A 0%, #F0A080 50%, #F5C0A0 100%);
}
.cover-icon { width: 42px; height: 42px; color: rgba(255,255,255,0.85); }
.cover-duration {
  position: absolute; bottom: 6px; right: 8px;
  font-size: 10px; color: rgba(255,255,255,0.85); background: rgba(0,0,0,0.35);
  padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono);
}

.card-body { padding: 14px; }
.card-title {
  font-size: var(--font-size-sm); font-weight: 600; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 4px;
}
.card-artist {
  font-size: 12px; color: var(--text-tertiary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 10px;
}
.card-meta { display: flex; align-items: center; gap: 8px; }
.card-score {
  display: flex; align-items: center; gap: 3px;
  font-size: 11px; color: var(--color-gold); font-weight: 600;
  margin-left: auto;
}
</style>

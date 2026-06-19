<template>
  <div class="content-detail-page">
    <header class="page-header">
      <div class="header-left">
        <button @click="goBack" class="back-btn">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 4l-6 6 6 6"/></svg>
        </button>
        <div>
          <h1>{{ content?.title || '内容详情' }}</h1>
          <p>内容元数据与推荐分析</p>
        </div>
      </div>
    </header>

    <div class="content-body" v-if="content">
      <!-- Basic info -->
      <div class="info-card surface-card">
        <div class="card-section">
          <h3>基本信息</h3>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">ID</span><span class="info-value">{{ content.content_id || content.id }}</span></div>
            <div class="info-item"><span class="info-label">类型</span><span :class="['badge', content.content_type === 'music' ? 'badge-indigo' : 'badge-amber']">{{ content.content_type === 'music' ? '音乐' : '视频' }}</span></div>
            <div class="info-item"><span class="info-label">标题</span><span class="info-value">{{ content.title || '-' }}</span></div>
            <div class="info-item"><span class="info-label">艺人/作者</span><span class="info-value">{{ content.artist_or_author || '-' }}</span></div>
            <div class="info-item"><span class="info-label">风格/分类</span><span class="info-value">{{ content.style_or_category || '-' }}</span></div>
            <div class="info-item"><span class="info-label">时长</span><span class="info-value">{{ content.duration ? content.duration + ' 秒' : '-' }}</span></div>
            <div class="info-item"><span class="info-label">语言</span><span class="info-value">{{ content.language || '-' }}</span></div>
            <div class="info-item" v-if="content.content_type === 'music'"><span class="info-label">BPM</span><span class="info-value">{{ content.bpm || '-' }}</span></div>
            <div class="info-item"><span class="info-label">热度</span><span class="info-value">{{ Number(content.hot_score || 0).toFixed(1) }}</span></div>
          </div>
        </div>
        <div class="card-section" v-if="tags.length">
          <h3>标签</h3>
          <div class="tags-list">
            <span v-for="tag in tags" :key="tag" class="badge badge-coral">{{ tag }}</span>
          </div>
        </div>
      </div>

      <!-- Recommendation reason -->
      <div class="info-card surface-card">
        <div class="card-section">
          <h3>推荐理由</h3>
          <div class="reason-list" v-if="content.source_strategy || content.reason">
            <div class="reason-item" v-if="content.source_strategy">
              <span class="reason-label">来源策略</span>
              <span :class="['badge', strategyBadge(content.source_strategy)]">{{ strategyLabel(content.source_strategy) }}</span>
            </div>
            <div class="reason-item" v-if="content.reason">
              <span class="reason-label">推荐原因</span>
              <span class="reason-text">{{ content.reason }}</span>
            </div>
            <div class="reason-item" v-if="content.score != null">
              <span class="reason-label">推荐分数</span>
              <span class="reason-value">{{ Number(content.score).toFixed(4) }}</span>
            </div>
            <div class="reason-item" v-if="content.source_rank != null">
              <span class="reason-label">原始排名</span>
              <span class="reason-value">#{{ content.source_rank }}</span>
            </div>
          </div>
          <div v-else class="reason-empty">
            <p>推荐理由由推荐引擎生成，实时数据更新后将显示在此处。</p>
            <span>包含：来源策略、推荐分数、原始排名、匹配原因</span>
          </div>
        </div>
      </div>

      <!-- Hot trend placeholder -->
      <div class="info-card surface-card" v-if="content.hot_score">
        <div class="card-section">
          <h3>热度数据</h3>
          <div class="stat-row">
            <div class="stat-item"><span class="stat-value">{{ Number(content.hot_score).toFixed(1) }}</span><span class="stat-label">热度评分</span></div>
            <div class="stat-item"><span class="stat-value">{{ (content.play_count || 0) }}</span><span class="stat-label">播放次数</span></div>
            <div class="stat-item"><span class="stat-value">{{ ((content.completion_rate || 0) * 100).toFixed(1) }}%</span><span class="stat-label">完播率</span></div>
            <div class="stat-item"><span class="stat-value">{{ ((content.interaction_rate || 0) * 100).toFixed(1) }}%</span><span class="stat-label">互动率</span></div>
          </div>
        </div>
      </div>

      <div v-if="!content" class="empty-state" style="padding:64px"><p>加载中...</p></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "@/api";

const route = useRoute();
const router = useRouter();
const content = ref(null);

const tags = computed(() => {
  const t = content.value?.tags;
  if (!t) return [];
  if (Array.isArray(t)) return t;
  try { return JSON.parse(t); } catch { return []; }
});

const strategyLabels = {
  coldstart_cluster: "冷启动聚类", als_cf: "ALS协同过滤", item2vec: "Item2Vec",
  hot: "热门", hot_rt: "实时热门", dpp_rerank: "DPP重排",
  epsilon_greedy: "Epsilon贪婪", content_based: "内容推荐", hybrid: "混合推荐",
};
function strategyLabel(s) { return strategyLabels[s] || s; }
function strategyBadge(s) {
  const m = { coldstart_cluster: "badge-coral", als_cf: "badge-indigo", item2vec: "badge-plum", hot: "badge-amber", dpp_rerank: "badge-teal", epsilon_greedy: "badge-sky" };
  return m[s] || "badge-gray";
}

function goBack() { router.back(); }

onMounted(async () => {
  const id = route.params.id;
  const type = route.query.type;
  try {
    const resp = await api.get(`/api/content/${id}${type ? `?type=${type}` : ""}`);
    content.value = resp.data.data;
  } catch (e) {
    console.error("Failed to load content:", e);
  }
});
</script>

<style scoped>
.content-detail-page { min-height: 100vh; background: var(--bg-root); color: var(--text-primary); }
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 28px; background: var(--bg-surface); border-bottom: 1px solid var(--border-subtle);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.header-left h1 { font-size: var(--font-size-lg); font-weight: 700; }
.header-left p  { font-size: var(--font-size-xs); color: var(--text-tertiary); }
.back-btn {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  color: var(--text-secondary); cursor: pointer; background: transparent;
  transition: all var(--duration-fast);
}
.back-btn:hover { background: rgba(232,120,74,0.08); color: var(--text-primary); }
.back-btn svg { width: 18px; height: 18px; }

.content-body { max-width: 900px; margin: 0 auto; padding: 28px 24px; display: flex; flex-direction: column; gap: 20px; }

.info-card { padding: 28px; border-radius: var(--radius-xl); }
.card-section { margin-bottom: 20px; }
.card-section:last-child { margin-bottom: 0; }
.card-section h3 { font-size: var(--font-size-base); font-weight: 700; margin-bottom: 14px; color: var(--text-primary); }

.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.info-item { display: flex; flex-direction: column; gap: 3px; }
.info-label { font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
.info-value { font-size: var(--font-size-sm); color: var(--text-primary); font-weight: 500; }

.tags-list { display: flex; flex-wrap: wrap; gap: 6px; }

.reason-list { display: flex; flex-direction: column; gap: 14px; }
.reason-item { display: flex; align-items: center; gap: 12px; }
.reason-label { font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; min-width: 70px; }
.reason-text { font-size: var(--font-size-sm); color: var(--text-primary); }
.reason-value { font-size: var(--font-size-sm); color: var(--text-primary); font-family: var(--font-mono); }

.reason-empty { text-align: center; padding: 24px 0; }
.reason-empty p { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: 4px; }
.reason-empty span { font-size: 11px; color: var(--text-tertiary); }

.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 16px; background: rgba(232,120,74,0.04); border-radius: var(--radius-md); }
.stat-value { font-size: var(--font-size-xl); font-weight: 800; color: var(--color-primary-dark); }
.stat-label { font-size: 11px; color: var(--text-tertiary); }

.empty-state { text-align: center; }
</style>

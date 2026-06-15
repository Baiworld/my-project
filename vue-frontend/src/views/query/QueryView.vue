<template>
  <div class="query-page">
    <!-- Header -->
    <header class="page-header">
      <div class="header-left">
        <button @click="goBack" class="back-btn" title="返回首页">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4l-6 6 6 6"/></svg>
        </button>
        <div>
          <h1>查询管理</h1>
          <p>推荐列表、内容管理与冷启动分析</p>
        </div>
      </div>
      <div class="header-right">
        <span class="header-badge">{{ activeTabLabel }}</span>
      </div>
    </header>

    <div class="query-content">
      <!-- Tabs -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="switchTab(tab.id)"
          :class="['tab-btn', { active: activeTab === tab.id }]"
        >
          {{ tab.name }}
        </button>
      </div>

      <!-- Search & Filter Bar -->
      <div class="search-card surface-card">
        <div class="search-row">
          <div class="search-input-wrap">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class="search-icon"><circle cx="9" cy="9" r="6"/><path d="M13.5 13.5L17 17" stroke-linecap="round"/></svg>
            <input
              v-model="queryForm.keyword"
              type="text"
              class="input-field search-field"
              :placeholder="keywordPlaceholder"
              @keyup.enter="executeQuery"
            />
          </div>
          <div class="filter-group">
            <select v-model="queryForm.content_type" class="select-field" aria-label="内容类型">
              <option value="">全部类型</option>
              <option value="music">音乐</option>
              <option value="video">视频</option>
            </select>
            <template v-if="activeTab === 'recommendations'">
              <select v-model="queryForm.strategy" class="select-field" aria-label="推荐策略">
                <option value="">全部策略</option>
                <option value="coldstart">冷启动聚类</option>
                <option value="als_cf">ALS协同过滤</option>
                <option value="item2vec">Item2Vec</option>
                <option value="hot">热门</option>
                <option value="dpp_rerank">DPP重排</option>
                <option value="epsilon_greedy">Epsilon贪婪</option>
              </select>
              <input v-model="queryForm.user_id" type="number" class="input-field user-id-field" placeholder="用户ID" @keyup.enter="executeQuery" />
            </template>
            <template v-if="activeTab === 'coldstart'">
              <select v-model="queryForm.time_filter" class="select-field" aria-label="时间范围">
                <option value="">全部时间</option>
                <option value="24h">近24小时</option>
                <option value="7d">近7天</option>
              </select>
              <select v-model.number="queryForm.cluster_id" class="select-field" aria-label="聚类">
                <option :value="null">全部集群</option>
                <option v-for="(c, idx) in clusterOptions" :key="idx" :value="idx">{{ c.name }} ({{ c.count }})</option>
              </select>
              <input v-model="queryForm.user_id" type="number" class="input-field user-id-field" placeholder="用户ID" @keyup.enter="executeQuery" />
            </template>
            <select v-model="queryForm.sort_by" class="select-field select-sm" aria-label="排序">
              <option v-for="s in activeSortOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
            <select v-model.number="queryForm.size" class="select-field select-sm" aria-label="每页数量">
              <option :value="10">10 条</option>
              <option :value="20">20 条</option>
              <option :value="50">50 条</option>
              <option :value="100">100 条</option>
            </select>
            <button @click="executeQuery" class="btn btn-primary">查询</button>
          </div>
        </div>
      </div>

      <!-- Coldstart Stats Card -->
      <div v-if="activeTab === 'coldstart' && coldstartStats" class="stats-row">
        <div class="stat-card surface-card">
          <span class="stat-value">{{ coldstartStats.total_coldstart_users }}</span>
          <span class="stat-label">冷启动用户总数</span>
        </div>
        <div class="stat-card surface-card">
          <span class="stat-value">{{ coldstartStats.active_coldstart_users_24h }}</span>
          <span class="stat-label">近24h活跃</span>
        </div>
        <div class="stat-card surface-card">
          <span class="stat-value">{{ coldstartStats.avg_behavior_count }}</span>
          <span class="stat-label">平均行为次数</span>
        </div>
        <div class="stat-card surface-card">
          <span class="stat-value">{{ coldstartStats.conversion_rate }}%</span>
          <span class="stat-label">转化率</span>
        </div>
      </div>

      <!-- Coldstart Strategy Distribution -->
      <div v-if="activeTab === 'coldstart' && coldstartStats?.strategy_distribution" class="strategy-bar surface-card">
        <span class="section-label">策略分布：</span>
        <span v-for="s in coldstartStats.strategy_distribution" :key="s.name" class="strategy-tag">
          {{ s.name }} <strong>{{ s.value }}</strong>
        </span>
      </div>

      <!-- Results Table -->
      <div class="results-card surface-card">
        <div class="results-header">
          <h3>查询结果</h3>
          <div class="results-actions" v-if="pagination.total > 0">
            <span class="result-count">{{ pagination.total }} 条记录</span>
            <button @click="exportData('csv')" class="btn btn-ghost btn-sm">CSV</button>
            <button @click="exportData('xlsx')" class="btn btn-ghost btn-sm">Excel</button>
          </div>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th v-for="col in activeColumns" :key="col.key" :class="col.align === 'right' ? 'align-right' : ''">
                  {{ col.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(item, idx) in queryResults"
                :key="item.id + '_' + idx"
                :style="{ animationDelay: `${idx * 0.02}s` }"
                class="row-fade-in"
                @click="openDetail(item)"
              >
                <td v-for="col in activeColumns" :key="col.key" :class="col.align === 'right' ? 'num-cell' : ''">
                  <template v-if="col.key === 'title'">
                    <span class="title-cell">{{ formatCell(item, col) }}</span>
                  </template>
                  <template v-else-if="col.key === 'type'">
                    <span :class="['badge', item.type === 'music' ? 'badge-indigo' : 'badge-amber']">
                      {{ item.type === 'music' ? '音乐' : '视频' }}
                    </span>
                  </template>
                  <template v-else-if="col.key === 'id'">
                    <span class="id-cell">{{ formatCell(item, col) }}</span>
                  </template>
                  <template v-else-if="col.key === 'coldstart_progress'">
                    <div class="progress-cell">
                      <div class="progress-bar-bg">
                        <div class="progress-bar-fill" :style="{ width: (item.coldstart_progress || 0) + '%' }"
                          :class="{ 'progress-near': (item.coldstart_progress || 0) >= 80 }"></div>
                      </div>
                      <span class="progress-text">{{ item.coldstart_progress || 0 }}%</span>
                    </div>
                  </template>
                  <template v-else-if="col.key === 'is_cold_start'">
                    <span :class="['badge', item.is_cold_start ? 'badge-amber' : 'badge-teal']">
                      {{ item.is_cold_start ? '是' : '否' }}
                    </span>
                  </template>
                  <template v-else>
                    {{ formatCell(item, col) }}
                  </template>
                </td>
              </tr>
            </tbody>
          </table>

          <div v-if="queryResults.length === 0 && !loading" class="empty-state">
            <svg viewBox="0 0 48 48" fill="none" class="empty-icon"><rect x="6" y="8" width="36" height="32" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M6 16h36" stroke="currentColor" stroke-width="1.5"/><circle cx="14" cy="12" r="1.5" fill="currentColor"/><circle cx="20" cy="12" r="1.5" fill="currentColor"/><circle cx="26" cy="12" r="1.5" fill="currentColor"/></svg>
            <p>暂无数据</p>
            <span>请设置查询条件后点击"查询"</span>
          </div>
          <div v-if="loading" class="empty-state"><p>加载中...</p></div>
        </div>

        <!-- Pagination -->
        <div v-if="pagination.total > 0" class="table-pagination">
          <span class="page-info">第 {{ pagination.page }} / {{ pagination.totalPages }} 页，共 {{ pagination.total }} 条</span>
          <div class="page-btns">
            <button @click="changePage(pagination.page - 1)" :disabled="pagination.page <= 1" class="btn btn-ghost btn-sm">← 上一页</button>
            <button @click="changePage(pagination.page + 1)" :disabled="pagination.page >= pagination.totalPages" class="btn btn-ghost btn-sm">下一页 →</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail Drawer -->
    <Teleport to="body">
      <div v-if="detailItem" class="drawer-overlay" @click.self="closeDetail">
        <div class="drawer-panel">
          <div class="drawer-header">
            <h3>{{ detailItem.title }}</h3>
            <button @click="closeDetail" class="drawer-close">✕</button>
          </div>
          <div class="drawer-body">
            <div class="detail-grid">
              <div class="detail-field" v-for="f in detailFields" :key="f.key">
                <span class="detail-label">{{ f.label }}</span>
                <span class="detail-value">{{ f.value }}</span>
              </div>
            </div>
            <div class="drawer-actions">
              <router-link
                v-if="detailItem.user_id"
                :to="`/query/user/${detailItem.user_id}`"
                class="btn btn-primary btn-sm"
              >
                查看用户画像 →
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import api from "@/api";

const router = useRouter();

const activeTab = ref("recommendations");
const loading = ref(false);
const tabs = [
  { id: "recommendations", name: "推荐列表" },
  { id: "content", name: "内容管理" },
  { id: "coldstart", name: "冷启动分析" },
];

const activeTabLabel = computed(() => tabs.find(t => t.id === activeTab.value)?.name || "");

const keywordPlaceholder = computed(() => {
  const map = {
    recommendations: "搜索标题、艺人、标签...",
    content: "搜索标题、艺人、标签...",
    coldstart: "搜索设备、渠道、兴趣标签...",
  };
  return map[activeTab.value] || "搜索...";
});

// ── Column definitions per tab ──
const columnsMap = {
  recommendations: [
    { key: "id", label: "内容ID", align: "left" },
    { key: "title", label: "标题", align: "left" },
    { key: "type", label: "类型", align: "left" },
    { key: "strategy", label: "策略", align: "left" },
    { key: "score", label: "推荐分数", align: "right" },
    { key: "hot_score", label: "热度", align: "right" },
    { key: "artist_or_author", label: "艺人/作者", align: "left" },
    { key: "style_or_category", label: "风格", align: "left" },
  ],
  content: [
    { key: "id", label: "内容ID", align: "left" },
    { key: "title", label: "标题", align: "left" },
    { key: "type", label: "类型", align: "left" },
    { key: "hot_score", label: "热度", align: "right" },
    { key: "play_count", label: "播放", align: "right" },
    { key: "like_count", label: "点赞", align: "right" },
    { key: "favorite_count", label: "收藏", align: "right" },
    { key: "share_count", label: "分享", align: "right" },
    { key: "completion_rate", label: "完播率", align: "right" },
    { key: "interaction_rate", label: "互动率", align: "right" },
    { key: "artist_or_author", label: "艺人/作者", align: "left" },
    { key: "style_or_category", label: "风格", align: "left" },
  ],
  coldstart: [
    { key: "id", label: "用户ID", align: "left" },
    { key: "coldstart_progress", label: "冷启进度", align: "left" },
    { key: "behavior_count", label: "行为次数", align: "right" },
    { key: "play_count", label: "播放", align: "right" },
    { key: "like_rate", label: "点赞率", align: "right" },
    { key: "favorite_rate", label: "收藏率", align: "right" },
    { key: "completion_rate", label: "完播率", align: "right" },
    { key: "cluster_name", label: "集群", align: "left" },
    { key: "device_type", label: "设备", align: "left" },
    { key: "register_channel", label: "注册渠道", align: "left" },
  ],
};

const activeColumns = computed(() => columnsMap[activeTab.value] || columnsMap.recommendations);

// ── Sort options per tab ──
const sortOptionsMap = {
  recommendations: [
    { value: "rank", label: "按排名" },
    { value: "score", label: "按分数" },
  ],
  content: [
    { value: "hot_score", label: "按热度" },
    { value: "play_count", label: "按播放数" },
  ],
  coldstart: [
    { value: "behavior_count", label: "按行为数" },
    { value: "play_count", label: "按播放数" },
    { value: "like_rate", label: "按点赞率" },
    { value: "completion_rate", label: "按完播率" },
  ],
};
const activeSortOptions = computed(() => sortOptionsMap[activeTab.value] || []);

// ── Query state ──
const queryForm = reactive({
  keyword: "",
  content_type: "",
  user_id: "",
  cluster_id: null,
  strategy: "",
  sort_by: "rank",
  time_filter: "",
  size: 20,
});

const queryResults = ref([]);
const pagination = reactive({ page: 1, size: 20, total: 0, totalPages: 0 });
const coldstartStats = ref(null);
const clusterOptions = ref([]);

// ── Detail drawer ──
const detailItem = ref(null);

const detailFields = computed(() => {
  if (!detailItem.value) return [];
  const item = detailItem.value;
  const fields = [];
  const skip = new Set(["id", "title", "type", "user_id"]);

  for (const [k, v] of Object.entries(item)) {
    if (skip.has(k) || v == null || v === "") continue;
    const label = fieldLabel(k);
    let value = v;
    if (typeof v === "number") {
      if (k.endsWith("_rate") || k.endsWith("_ratio")) {
        value = (v * 100).toFixed(1) + "%";
      } else if (k.endsWith("_score") || k === "score" || k === "hot_score") {
        value = v.toFixed(4);
      } else if (Number.isInteger(v)) {
        value = v.toLocaleString();
      } else {
        value = v.toFixed(2);
      }
    }
    if (k === "duration") value = v + "s";
    if (k === "bpm") value = v;
    if (k === "tags" || k === "interest_tags") {
      try { value = typeof v === "string" ? JSON.parse(v).join(", ") : v; } catch {}
    }
    if (k === "content_type_ratio") {
      try {
        const r = typeof v === "string" ? JSON.parse(v) : v;
        value = Object.entries(r).map(([k, n]) => `${k}: ${(n * 100).toFixed(0)}%`).join(" / ");
      } catch {}
    }
    fields.push({ key: k, label, value: String(value) });
  }
  return fields;
});

function fieldLabel(key) {
  const map = {
    artist_or_author: "艺人/作者", style_or_category: "风格/分类", tags: "标签",
    duration: "时长", language: "语言", bpm: "BPM",
    play_count: "播放数", like_count: "点赞数", favorite_count: "收藏数",
    share_count: "分享数", comment_count: "评论数",
    completion_rate: "完播率", interaction_rate: "互动率",
    like_rate: "点赞率", favorite_rate: "收藏率", skip_rate: "跳过率",
    behavior_count: "行为次数", content_type_ratio: "内容偏好",
    cluster_id: "聚类ID", cluster_name: "集群名称", device_type: "设备类型", register_channel: "注册渠道",
    interest_tags: "兴趣标签", is_cold_start: "冷启动标记",
    hot_score: "热度", score: "分数", rank: "排名",
    reason: "推荐理由", strategy: "推荐策略",
  };
  return map[key] || key;
}

function formatCell(item, col) {
  const v = item[col.key];
  if (v == null || v === "") return "-";
  if (col.key.endsWith("_rate") || col.key.endsWith("_ratio")) {
    return (Number(v) * 100).toFixed(1) + "%";
  }
  if (col.key === "hot_score" || col.key === "score") {
    return Number(v).toFixed(2);
  }
  if (col.key === "cluster_id" && v != null) return "集群 #" + (Number(v) + 1);
  if (col.key === "strategy") {
    const m = { hot: "热门", hot_rt: "实时热门", als_cf: "ALS协同过滤", item2vec: "Item2Vec",
                coldstart_cluster: "冷启动聚类", dpp_rerank: "DPP重排", epsilon_greedy: "Epsilon贪婪" };
    return m[v] || v;
  }
  return String(v);
}

// ── Actions ──
function switchTab(tabId) {
  if (activeTab.value === tabId) return;
  activeTab.value = tabId;
  resetQuery();
}

function resetQuery() {
  queryForm.keyword = "";
  queryForm.content_type = "";
  queryForm.user_id = "";
  queryForm.cluster_id = null;
  queryForm.strategy = "";
  queryForm.sort_by = activeTab.value === "recommendations" ? "rank" : (activeTab.value === "coldstart" ? "behavior_count" : "hot_score");
  queryForm.time_filter = "";
  queryForm.page = 1;
  queryResults.value = [];
  pagination.total = 0;
  pagination.totalPages = 0;
  coldstartStats.value = null;
  clusterOptions.value = [];
}

async function executeQuery() {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (queryForm.keyword) params.append("keyword", queryForm.keyword);
    if (queryForm.content_type) params.append("content_type", queryForm.content_type);
    if (queryForm.user_id) params.append("user_id", queryForm.user_id);
    if (queryForm.strategy && activeTab.value === "recommendations") params.append("strategy", queryForm.strategy);
    if (queryForm.sort_by) params.append("sort_by", queryForm.sort_by);
    if (queryForm.time_filter && activeTab.value === "coldstart") params.append("time_filter", queryForm.time_filter);
    params.append("page", String(pagination.page));
    params.append("size", String(queryForm.size));

    const endpointMap = {
      recommendations: "/api/recommendations",
      content: "/api/content",
      coldstart: "/api/coldstart/analysis",
    };
    const endpoint = endpointMap[activeTab.value];

    if (activeTab.value === "coldstart" && queryForm.cluster_id != null) {
      params.append("cluster_id", String(queryForm.cluster_id));
    }

    const response = await api.get(`${endpoint}?${params}`);
    queryResults.value = response.data.data || response.data;

    if (response.data.pagination) {
      pagination.page = response.data.pagination.page;
      pagination.size = response.data.pagination.size;
      pagination.total = response.data.pagination.total;
      pagination.totalPages = Math.max(1, Math.ceil(pagination.total / pagination.size));
    }
  } catch (error) {
    console.error("查询失败:", error);
    queryResults.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadColdstartStats() {
  try {
    const resp = await api.get("/api/coldstart/stats");
    if (resp.data?.code === 200) {
      coldstartStats.value = resp.data.data;
      const dist = resp.data.data.cluster_distribution || [];
      clusterOptions.value = dist.map(c => ({ name: c.cluster_name, count: c.count }));
    }
  } catch {}
}

watch(activeTab, (tab) => {
  if (tab === "coldstart") loadColdstartStats();
});

function changePage(page) {
  if (page < 1 || page > pagination.totalPages) return;
  pagination.page = page;
  executeQuery();
}

const exportTableMap = { recommendations: "offline_recommendations", content: "rt_content_hot", coldstart: "rt_coldstart_cluster" };

async function exportData(format) {
  const table = exportTableMap[activeTab.value] || "recommendations";
  try {
    const response = await api.export.download(table, format);
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${table}.${format === "csv" ? "csv" : "xlsx"}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    console.error("导出失败:", e);
  }
}

function openDetail(item) {
  detailItem.value = item;
}

function closeDetail() {
  detailItem.value = null;
}

function goBack() {
  router.push("/dashboard");
}

onMounted(() => {
  executeQuery();
});
</script>

<style scoped>
.query-page { min-height: 100vh; background: var(--bg-root); color: var(--text-primary); }

/* ── Header ── */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 28px;
  background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,248,243,0.9));
  border-bottom: 1px solid var(--border-subtle);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.header-left h1 {
  font-size: var(--font-size-lg); font-weight: 700;
  background: linear-gradient(135deg, var(--color-primary-dark), var(--color-amber-dark));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.header-left p { font-size: var(--font-size-xs); color: var(--text-tertiary); margin-top: 1px; }
.back-btn {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, rgba(232,120,74,0.06), rgba(245,158,11,0.04));
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  color: var(--text-secondary); cursor: pointer;
  transition: all var(--duration-fast);
}
.back-btn:hover { background: rgba(232,120,74,0.12); color: var(--color-primary-dark); border-color: var(--border-accent); }
.back-btn svg { width: 18px; height: 18px; }
.header-badge {
  font-size: var(--font-size-xs); color: var(--color-bronze);
  background: linear-gradient(135deg, rgba(232,120,74,0.08), rgba(245,158,11,0.05));
  padding: 5px 14px; border-radius: 99px; border: 1px solid var(--border-subtle);
}

.query-content { max-width: 1300px; margin: 0 auto; padding: 28px 24px; }

/* Tab bar */
.tab-bar { display: flex; gap: 6px; margin-bottom: 22px; }
.tab-btn {
  padding: 9px 22px; border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  background: transparent; color: var(--text-secondary); cursor: pointer;
  font-size: var(--font-size-sm); font-weight: 500;
  transition: all var(--duration-fast);
}
.tab-btn:hover { background: rgba(232,120,74,0.06); color: var(--text-primary); border-color: var(--border-default); }
.tab-btn.active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-color: var(--color-primary); color: #fff;
  box-shadow: 0 2px 8px var(--color-primary-glow);
}

/* Search card */
.search-card {
  padding: 18px 22px; margin-bottom: 22px;
  background: linear-gradient(180deg, var(--bg-surface), var(--bg-surface-warm));
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}
.search-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.search-input-wrap {
  flex: 1; min-width: 220px; display: flex; align-items: center; gap: 8px;
  background: rgba(232,120,74,0.04); border: 1px solid var(--border-default);
  border-radius: var(--radius-md); padding: 0 12px;
  transition: border-color var(--duration-fast);
}
.search-input-wrap:focus-within { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-glow); }
.search-icon { width: 16px; height: 16px; color: var(--text-tertiary); flex-shrink: 0; }
.search-field { border: none !important; background: transparent !important; padding: 9px 0; flex: 1; }
.filter-group { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.user-id-field { width: 130px; }
.select-sm { width: 85px; }

/* Stats */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px; }
.stat-card {
  padding: 18px 14px; display: flex; flex-direction: column; align-items: center; gap: 6px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, var(--bg-surface), var(--bg-surface-warm));
  border: 1px solid var(--border-subtle);
  transition: all var(--duration-fast);
}
.stat-card:nth-child(1) { border-top: 3px solid var(--color-primary); }
.stat-card:nth-child(2) { border-top: 3px solid var(--color-amber); }
.stat-card:nth-child(3) { border-top: 3px solid var(--color-teal); }
.stat-card:nth-child(4) { border-top: 3px solid var(--color-indigo); }
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat-value {
  font-size: var(--font-size-2xl); font-weight: 800;
  background: linear-gradient(135deg, var(--color-primary-dark), var(--color-amber-dark));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.stat-label { font-size: var(--font-size-xs); color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.strategy-bar {
  padding: 12px 20px; margin-bottom: 18px; display: flex; align-items: center; gap: 10px;
  flex-wrap: wrap; border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(232,120,74,0.03), rgba(245,158,11,0.02));
}
.section-label { font-size: var(--font-size-xs); color: var(--text-secondary); font-weight: 600; }
.strategy-tag {
  font-size: var(--font-size-xs); padding: 4px 12px; border-radius: 99px;
  background: linear-gradient(135deg, rgba(232,120,74,0.1), rgba(245,158,11,0.06));
  color: var(--color-bronze-dark); border: 1px solid var(--border-subtle);
}
.strategy-tag strong { color: var(--color-primary-dark); margin-left: 4px; }

/* Table */
.results-card {
  overflow: hidden;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
}
.results-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 22px 12px;
  background: linear-gradient(180deg, rgba(255,248,243,0.5), transparent);
  border-bottom: 1px solid var(--border-subtle);
}
.results-header h3 { font-size: var(--font-size-base); font-weight: 700; color: var(--text-primary); }
.results-actions { display: flex; align-items: center; gap: 10px; }
.result-count { font-size: var(--font-size-xs); color: var(--text-tertiary); }
.table-wrap { padding: 0; overflow-x: auto; }
.data-table tbody tr {
  cursor: pointer;
  transition: all var(--duration-fast);
}
.data-table tbody tr:hover {
  background: linear-gradient(90deg, rgba(232,120,74,0.05), rgba(245,158,11,0.02));
}
.id-cell { font-family: var(--font-mono); font-size: var(--font-size-xs); color: var(--text-tertiary); }
.title-cell { max-width: 240px; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.num-cell { font-family: var(--font-mono); font-size: var(--font-size-sm); }
.align-right { text-align: right; }
.row-fade-in { animation: fadeIn 0.3s ease both; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 64px 20px; text-align: center;
}
.empty-icon { width: 56px; height: 56px; color: var(--text-tertiary); margin-bottom: 16px; opacity: 0.4; }
.empty-state p { font-size: var(--font-size-base); color: var(--text-secondary); margin-bottom: 4px; }
.empty-state span { font-size: var(--font-size-xs); color: var(--text-tertiary); }

.table-pagination {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 22px; border-top: 1px solid var(--border-subtle);
  background: var(--bg-surface-warm);
}
.page-info { font-size: var(--font-size-xs); color: var(--text-tertiary); }
.page-btns { display: flex; gap: 8px; }

/* ── Drawer ── */
.drawer-overlay {
  position: fixed; inset: 0; background: rgba(40,20,10,0.45);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  z-index: 2000; display: flex; justify-content: flex-end;
}
.drawer-panel {
  width: 440px; max-width: 92vw; height: 100%;
  background: linear-gradient(180deg, var(--bg-surface), var(--bg-surface-warm));
  border-left: 1px solid var(--border-accent);
  overflow-y: auto; box-shadow: -8px 0 32px rgba(120,80,50,0.1);
  animation: slideInRight 0.28s var(--ease-out-expo);
}
.drawer-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 22px 24px;
  background: linear-gradient(180deg, rgba(232,120,74,0.04), transparent);
  border-bottom: 1px solid var(--border-subtle);
}
.drawer-header h3 {
  font-size: var(--font-size-lg); font-weight: 700;
  background: linear-gradient(135deg, var(--text-primary), var(--color-bronze-dark));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.drawer-close {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  background: rgba(232,120,74,0.06); border: 1px solid var(--border-subtle);
  border-radius: 8px; color: var(--text-secondary); font-size: 16px; cursor: pointer;
  transition: all var(--duration-fast);
}
.drawer-close:hover { background: rgba(232,120,74,0.14); color: var(--text-primary); border-color: var(--border-default); }
.drawer-body { padding: 22px 24px; }
.detail-grid { display: flex; flex-direction: column; gap: 14px; }
.detail-field { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; padding: 6px 0; border-bottom: 1px solid var(--border-subtle); }
.detail-label { font-size: var(--font-size-xs); color: var(--text-tertiary); white-space: nowrap; font-weight: 600; }
.detail-value { font-size: var(--font-size-sm); color: var(--text-primary); text-align: right; word-break: break-all; font-weight: 500; }
.drawer-actions { margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--border-subtle); }

/* ── Progress bar ── */
.progress-cell { display: flex; align-items: center; gap: 10px; min-width: 120px; }
.progress-bar-bg {
  flex: 1; height: 6px; background: rgba(200,132,90,0.08); border-radius: 3px; overflow: hidden;
}
.progress-bar-fill {
  height: 100%; border-radius: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-amber));
  transition: width 0.5s var(--ease-out-expo);
}
.progress-bar-fill.progress-near { background: linear-gradient(90deg, var(--color-amber), var(--color-rose)); }
.progress-text { font-family: var(--font-mono); font-size: var(--font-size-xs); color: var(--text-secondary); width: 42px; text-align: right; }

@keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
</style>

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

      <!-- Search form -->
      <div class="search-card surface-card anim-fade-in-up">
        <div class="search-header">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class="search-icon-title"><circle cx="9" cy="9" r="6"/><path d="M13.5 13.5L17 17" stroke-linecap="round"/></svg>
          <h3>查询条件</h3>
        </div>
        <div class="search-grid">
          <div class="field">
            <label>用户 ID</label>
            <input v-model="queryForm.user_id" type="number" class="input-field" placeholder="输入用户 ID" />
          </div>
          <div class="field">
            <label>内容类型</label>
            <select v-model="queryForm.content_type" class="select-field">
              <option value="">全部类型</option>
              <option value="music">🎵 音乐</option>
              <option value="video">🎬 视频</option>
            </select>
          </div>
          <div class="field">
            <label>页码</label>
            <input v-model.number="queryForm.page" type="number" min="1" class="input-field" />
          </div>
          <div class="field">
            <label>每页数量</label>
            <select v-model.number="queryForm.size" class="select-field">
              <option :value="10">10 条</option>
              <option :value="20">20 条</option>
              <option :value="50">50 条</option>
              <option :value="100">100 条</option>
            </select>
          </div>
        </div>
        <button @click="executeQuery" class="btn btn-primary">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7" cy="7" r="5"/><path d="M11 11l3.5 3.5" stroke-linecap="round"/></svg>
          执行查询
        </button>
      </div>

      <!-- Results table -->
      <div class="results-card surface-card anim-fade-in-up">
        <div class="results-header">
          <h3>查询结果</h3>
          <span v-if="pagination.total > 0" class="result-count">{{ pagination.total }} 条记录</span>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>标题</th>
                <th>类型</th>
                <th>热度</th>
                <th>推荐分数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in queryResults" :key="item.id" :style="{ animationDelay: `${idx * 0.03}s` }" class="row-fade-in">
                <td class="id-cell">{{ item.id }}</td>
                <td class="title-cell">{{ item.title }}</td>
                <td>
                  <span :class="['badge', item.type === 'music' ? 'badge-blue' : 'badge-yellow']">
                    {{ item.type === 'music' ? '音乐' : '视频' }}
                  </span>
                </td>
                <td class="num-cell">{{ item.hot_score?.toFixed(2) || '-' }}</td>
                <td class="num-cell score-cell">{{ item.score?.toFixed(4) || '-' }}</td>
              </tr>
            </tbody>
          </table>

          <!-- Empty state -->
          <div v-if="queryResults.length === 0" class="empty-state">
            <svg viewBox="0 0 48 48" fill="none" class="empty-icon"><rect x="6" y="8" width="36" height="32" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M6 16h36" stroke="currentColor" stroke-width="1.5"/><circle cx="14" cy="12" r="1.5" fill="currentColor"/><circle cx="20" cy="12" r="1.5" fill="currentColor"/><circle cx="26" cy="12" r="1.5" fill="currentColor"/></svg>
            <p>暂无数据</p>
            <span>请设置查询条件后点击"执行查询"</span>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="pagination.total > 0" class="table-pagination">
          <span class="page-info">第 {{ pagination.page }} / {{ pagination.totalPages }} 页，共 {{ pagination.total }} 条</span>
          <div class="page-btns">
            <button @click="changePage(pagination.page - 1)" :disabled="pagination.page <= 1" class="btn btn-ghost btn-sm">
              ← 上一页
            </button>
            <button @click="changePage(pagination.page + 1)" :disabled="pagination.page >= pagination.totalPages" class="btn btn-ghost btn-sm">
              下一页 →
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from "vue";
import { useRouter } from "vue-router";
import api from "@/api";

const router = useRouter();

const activeTab = ref("recommendations");
const tabs = [
  { id: "recommendations", name: "推荐列表" },
  { id: "content", name: "内容管理" },
  { id: "coldstart", name: "冷启动分析" },
];

const activeTabLabel = computed(() => tabs.find(t => t.id === activeTab.value)?.name || "");

const queryForm = reactive({
  user_id: "",
  content_type: "",
  page: 1,
  size: 20,
});

const queryResults = ref([]);
const pagination = reactive({
  page: 1, size: 20, total: 0, totalPages: 0,
});

function switchTab(tabId) {
  if (activeTab.value === tabId) return;
  activeTab.value = tabId;
  queryForm.page = 1;
  queryResults.value = [];
  pagination.total = 0;
  pagination.totalPages = 0;
}

// Auto-query when switching tabs
watch(activeTab, () => {
  // Clear old results so user sees the tab has changed
  queryResults.value = [];
  pagination.total = 0;
  pagination.totalPages = 0;
});

async function executeQuery() {
  try {
    const params = new URLSearchParams();
    if (queryForm.user_id) params.append("user_id", queryForm.user_id);
    if (queryForm.content_type) params.append("content_type", queryForm.content_type);
    params.append("page", queryForm.page);
    params.append("size", queryForm.size);

    const endpoint = activeTab.value === "recommendations"
      ? "/api/recommendations"
      : activeTab.value === "content"
        ? "/api/content"
        : "/api/coldstart/analysis";

    const response = await api.get(`${endpoint}?${params}`);
    queryResults.value = response.data.data || response.data;

    if (response.data.pagination) {
      pagination.page = response.data.pagination.page;
      pagination.size = response.data.pagination.size;
      pagination.total = response.data.pagination.total;
      pagination.totalPages = Math.ceil(pagination.total / pagination.size);
    }
  } catch (error) {
    console.error("查询失败:", error);
    queryResults.value = [];
  }
}

function changePage(page) {
  if (page < 1 || page > pagination.totalPages) return;
  queryForm.page = page;
  executeQuery();
}

function goBack() {
  router.push("/dashboard");
}
</script>

<style scoped>
.query-page {
  min-height: 100vh;
  background: var(--bg-root);
  color: var(--text-primary);
}

/* ── Header ── */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.header-left h1 { font-size: var(--font-size-lg); font-weight: 700; }
.header-left p  { font-size: var(--font-size-xs); color: var(--text-tertiary); margin-top: 1px; }

.back-btn {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); color: var(--text-secondary); cursor: pointer;
  transition: all var(--duration-fast) ease;
}
.back-btn:hover { background: rgba(255,255,255,0.08); color: var(--text-primary); }
.back-btn svg { width: 18px; height: 18px; }

.header-badge {
  font-size: var(--font-size-xs); color: var(--text-secondary);
  background: rgba(255,255,255,0.04); padding: 5px 14px; border-radius: 99px;
}

/* ── Content ── */
.query-content { max-width: 1200px; margin: 0 auto; padding: 24px; }

/* ── Tabs ── */
.tab-bar { display: flex; gap: 6px; margin-bottom: 20px; }

/* ── Search card ── */
.search-card { padding: 24px; margin-bottom: 20px; }
.search-header { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
.search-header h3 { font-size: var(--font-size-base); font-weight: 600; }
.search-icon-title { width: 18px; height: 18px; color: var(--text-secondary); }
.search-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.field { display: flex; flex-direction: column; gap: 6px; }
.field label {
  font-size: var(--font-size-xs); font-weight: 500;
  color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em;
}

/* ── Results card ── */
.results-card { overflow: hidden; }
.results-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px 0;
}
.results-header h3 { font-size: var(--font-size-base); font-weight: 600; }
.result-count { font-size: var(--font-size-xs); color: var(--text-tertiary); }

.table-wrap { padding: 12px 0 0; overflow-x: auto; }

.id-cell { font-family: var(--font-mono); font-size: var(--font-size-xs); color: var(--text-tertiary); }
.title-cell { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.num-cell { font-family: var(--font-mono); font-size: var(--font-size-sm); }
.score-cell { color: #A5B4FC; }

.row-fade-in { animation: fadeIn 0.35s ease both; }

/* ── Empty state ── */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 56px 20px; text-align: center;
}
.empty-icon { width: 56px; height: 56px; color: var(--text-tertiary); margin-bottom: 16px; opacity: 0.5; }
.empty-state p  { font-size: var(--font-size-base); color: var(--text-secondary); margin-bottom: 4px; }
.empty-state span { font-size: var(--font-size-xs); color: var(--text-tertiary); }

/* ── Pagination ── */
.table-pagination {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; border-top: 1px solid var(--border-subtle);
}
.page-info { font-size: var(--font-size-xs); color: var(--text-tertiary); }
.page-btns { display: flex; gap: 8px; }
</style>

<template>
  <div class="dashboard">
    <!-- ═══ Sidebar ═══ -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 36 36" fill="none">
            <rect width="36" height="36" rx="10" fill="url(#side-logo-grad)"/>
            <path d="M10 26V12l8 8 8-8v14" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            <defs><linearGradient id="side-logo-grad" x1="0" y1="0" x2="36" y2="36"><stop stop-color="#6366F1"/><stop offset="1" stop-color="#8B5CF6"/></linearGradient></defs>
          </svg>
        </div>
        <div>
          <h2>推荐系统</h2>
          <p>数据大屏</p>
        </div>
      </div>

      <nav class="sidebar-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="['nav-item', { active: activeTab === tab.id }]"
        >
          <span class="nav-icon" v-html="tab.icon"></span>
          <span class="nav-label">{{ tab.name }}</span>
          <span v-if="activeTab === tab.id" class="nav-indicator"></span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="ws-status">
          <span :class="['ws-dot', wsConnected ? 'on' : 'off']"></span>
          <span>{{ wsConnected ? '实时连接' : '未连接' }}</span>
        </div>
      </div>
    </aside>

    <!-- ═══ Main content ═══ -->
    <div class="main-area">
      <!-- Header -->
      <header class="top-bar">
        <div class="top-left">
          <h1>{{ activeTabLabel }}</h1>
          <span class="top-time">{{ currentTime }}</span>
        </div>
        <div class="top-right">
          <div class="header-actions">
            <router-link to="/query" class="btn btn-ghost btn-sm" v-if="canQuery">查询管理</router-link>
            <router-link to="/admin" class="btn btn-ghost btn-sm" v-if="canAdmin">系统管理</router-link>
          </div>
          <button @click="handleLogout" class="btn btn-ghost btn-sm logout-btn">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M6 14H3.3A1.3 1.3 0 012 12.7V3.3A1.3 1.3 0 013.3 2H6M11 11l3-3-3-3M14 8H6"/></svg>
            退出
          </button>
        </div>
      </header>

      <!-- Content scroll area -->
      <div class="content-scroll">
        <div class="content-inner">

          <!-- ════════════════════════════════════════════ -->
          <!-- Tab: 实时监控 -->
          <!-- ════════════════════════════════════════════ -->
          <template v-if="activeTab === 'realtime'">
            <div class="stagger">
              <div class="metrics-row">
                <MetricCard title="实时在线用户" :value="dashboardStore.metrics.onlineUsers" unit="人" trend="+12.5%" trendType="up" accent="blue" icon="users" />
                <MetricCard title="今日推荐总数" :value="dashboardStore.metrics.todayRecommendations" unit="次" trend="+8.3%" trendType="up" accent="green" icon="target" />
                <MetricCard title="今日 CTR" :value="(dashboardStore.metrics.todayCTR * 100).toFixed(2) + '%'" unit="" trend="-1.2%" trendType="down" accent="purple" icon="trend" />
                <MetricCard title="人均播放时长" :value="formatDuration(dashboardStore.metrics.avgWatchDuration)" unit="" trend="+5.8%" trendType="up" accent="orange" icon="clock" />
              </div>

              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>CTR 趋势</h3><span class="panel-badge">近 7 天</span></div>
                  <div class="panel-body"><TrendLineChart :data="dashboardStore.trendData.ctr" /></div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>内容热度 Top 10</h3><span class="panel-badge">实时更新</span></div>
                  <div class="panel-body"><HotBarChart :data="dashboardStore.hotContent" /></div>
                </div>
              </div>

              <div class="chart-panel log-panel">
                <div class="panel-header">
                  <h3>实时行为日志</h3>
                  <div class="panel-actions">
                    <span class="log-count">{{ dashboardStore.eventLogs.length }} 条</span>
                    <button @click="dashboardStore.clearEventLogs" class="btn btn-ghost btn-sm">清空</button>
                  </div>
                </div>
                <div class="panel-body"><ScrollLog :logs="dashboardStore.eventLogs" /></div>
              </div>
            </div>
          </template>

          <!-- ════════════════════════════════════════════ -->
          <!-- Tab: 趋势分析 -->
          <!-- ════════════════════════════════════════════ -->
          <template v-if="activeTab === 'trend'">
            <div class="stagger">
              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>CTR 趋势</h3><span class="panel-badge">近 7 天</span></div>
                  <div class="panel-body"><TrendLineChart :data="dashboardStore.trendData.ctr" /></div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>内容热度 Top 10</h3><span class="panel-badge">实时更新</span></div>
                  <div class="panel-body"><HotBarChart :data="dashboardStore.hotContent" /></div>
                </div>
              </div>
              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>音乐 / 视频占比</h3></div>
                  <div class="panel-body">
                    <DonutChart :data="[{ name: '音乐', value: dashboardStore.musicVideoRatio.music }, { name: '视频', value: dashboardStore.musicVideoRatio.video }]" />
                  </div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>CTR 与推荐数量趋势</h3></div>
                  <div class="panel-body" style="display:flex;align-items:center;justify-content:center;min-height:260px">
                    <div style="text-align:center">
                      <div style="font-size:48px;font-weight:700;color:#818CF8">{{ (dashboardStore.metrics.todayCTR * 100).toFixed(2) }}%</div>
                      <div style="color:var(--text-secondary);margin-top:4px">今日点击率</div>
                      <div style="font-size:32px;font-weight:700;color:#34D399;margin-top:20px">{{ dashboardStore.metrics.todayRecommendations.toLocaleString() }}</div>
                      <div style="color:var(--text-secondary);margin-top:4px">今日推荐总数</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- ════════════════════════════════════════════ -->
          <!-- Tab: 冷启动分析 -->
          <!-- ════════════════════════════════════════════ -->
          <template v-if="activeTab === 'coldstart'">
            <div class="stagger">
              <div class="metrics-row">
                <MetricCard title="冷启动用户数" :value="dashboardStore.coldstartStats.newUsers || 432" unit="人" trend="+15.3%" trendType="up" accent="blue" icon="users" />
                <MetricCard title="聚类数量" :value="dashboardStore.clusterDistribution.length || 8" unit="个" trend="" trendType="up" accent="green" icon="target" />
                <MetricCard title="平均行为次数" :value="23" unit="次" trend="+3.2%" trendType="up" accent="purple" icon="trend" />
                <MetricCard title="冷启动转化率" :value="'32.5%'" unit="" trend="+5.1%" trendType="up" accent="orange" icon="clock" />
              </div>
              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>冷启动用户聚类分布</h3></div>
                  <div class="panel-body"><ClusterPieChart :data="dashboardStore.clusterDistribution" /></div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>冷启动转化漏斗</h3></div>
                  <div class="panel-body"><FunnelChart :data="funnelData" /></div>
                </div>
              </div>
            </div>
          </template>

          <!-- ════════════════════════════════════════════ -->
          <!-- Tab: 推荐效果 -->
          <!-- ════════════════════════════════════════════ -->
          <template v-if="activeTab === 'recommendations'">
            <div class="stagger">
              <div class="metrics-row">
                <MetricCard title="今日推荐总数" :value="dashboardStore.metrics.todayRecommendations" unit="次" trend="+8.3%" trendType="up" accent="green" icon="target" />
                <MetricCard title="今日 CTR" :value="(dashboardStore.metrics.todayCTR * 100).toFixed(2) + '%'" unit="" trend="-1.2%" trendType="down" accent="purple" icon="trend" />
                <MetricCard title="人均播放时长" :value="formatDuration(dashboardStore.metrics.avgWatchDuration)" unit="" trend="+5.8%" trendType="up" accent="orange" icon="clock" />
                <MetricCard title="推荐覆盖率" :value="'78.3%'" unit="" trend="+2.1%" trendType="up" accent="blue" icon="users" />
              </div>
              <div class="chart-row cols-3">
                <div class="chart-panel">
                  <div class="panel-header"><h3>音乐 / 视频占比</h3></div>
                  <div class="panel-body">
                    <DonutChart :data="[{ name: '音乐', value: dashboardStore.musicVideoRatio.music }, { name: '视频', value: dashboardStore.musicVideoRatio.video }]" />
                  </div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>CTR 趋势</h3></div>
                  <div class="panel-body"><TrendLineChart :data="dashboardStore.trendData.ctr" /></div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>内容热度 Top 10</h3></div>
                  <div class="panel-body"><HotBarChart :data="dashboardStore.hotContent" /></div>
                </div>
              </div>
            </div>
          </template>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useDashboardStore } from "@/stores/dashboard";
import { useWebSocket } from "@/composables/useWebSocket";
import MetricCard from "./components/MetricCard.vue";
import TrendLineChart from "./components/TrendLineChart.vue";
import HotBarChart from "./components/HotBarChart.vue";
import DonutChart from "./components/DonutChart.vue";
import ClusterPieChart from "./components/ClusterPieChart.vue";
import FunnelChart from "./components/FunnelChart.vue";
import ScrollLog from "./components/ScrollLog.vue";

const router = useRouter();
const authStore = useAuthStore();
const dashboardStore = useDashboardStore();
const { connected: wsConnected, connect: wsConnect, on: wsOn } = useWebSocket();

const activeTab = ref("realtime");
const currentTime = ref("");

const canQuery = computed(() => authStore.hasRole("operator") || authStore.hasRole("admin"));
const canAdmin = computed(() => authStore.hasRole("admin"));

const tabs = [
  { id: "realtime", name: "实时监控", icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l3 2"/></svg>' },
  { id: "trend", name: "趋势分析", icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 18L8 10l4 4 6-8"/><path d="M14 6h4v4"/></svg>' },
  { id: "coldstart", name: "冷启动分析", icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="10" r="8"/><path d="M10 2v4M10 14v4M2 10h4M14 10h4"/></svg>' },
  { id: "recommendations", name: "推荐效果", icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 10l3 3 5-6"/><circle cx="10" cy="10" r="8"/></svg>' },
];

const activeTabLabel = computed(() => tabs.find(t => t.id === activeTab.value)?.name || "");

const funnelData = computed(() => {
  const clusterData = dashboardStore.clusterDistribution;
  if (!clusterData || clusterData.length === 0) return [];
  const total = clusterData.reduce((s, c) => s + (c.count || c.value || 0), 0) || 1;
  const colors = ["#6366F1", "#818CF8", "#A5B4FC", "#34D399", "#6EE7B7"];
  return clusterData.slice(0, 5).map((c, i) => ({
    value: Math.round(((c.count || c.value || 0) / total) * 100),
    name: c.cluster_name || c.name || `聚类 ${i + 1}`,
    itemStyle: { color: colors[i % colors.length] },
  }));
});

function formatDuration(seconds) {
  if (!seconds) return "00:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function handleLogout() {
  authStore.logout();
  router.push("/login");
}

function updateTime() {
  currentTime.value = new Date().toLocaleString("zh-CN", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false,
  });
}

let timeInterval;

onMounted(async () => {
  updateTime();
  timeInterval = setInterval(updateTime, 1000);

  await Promise.all([
    dashboardStore.loadMetrics(),
    dashboardStore.loadTrendData(),
    dashboardStore.loadHotContent(),
    dashboardStore.loadColdstartAnalysis(),
  ]);

  wsConnect();
  wsOn("dashboard_update", (msg) => {
    if (!msg || msg.type !== "dashboard_snapshot") return;
    const d = msg.data;
    if (d) {
      dashboardStore.metrics = {
        onlineUsers: d.online_users || 0,
        todayRecommendations: d.daily_recommendations || 0,
        todayCTR: d.ctr || 0,
        avgWatchDuration: d.avg_watch_duration || 0,
      };
      if (d.hot_content_top5) dashboardStore.hotContent = d.hot_content_top5;
      if (d.coldstart_new_today != null) dashboardStore.coldstartStats.newUsers = d.coldstart_new_today;
    }
  });
  wsOn("user_event", (msg) => {
    const d = msg?.data;
    if (d) {
      dashboardStore.addEventLog({
        user_id: d.user_id || 0,
        event_type: d.event_type || "未知",
        content_type: d.content_type || "音乐",
        content_id: d.content_id || 0,
      });
    }
  });
});

onUnmounted(() => {
  clearInterval(timeInterval);
});
</script>

<style scoped>
/* ═══════ Layout ═══════ */
.dashboard {
  display: flex;
  height: 100vh;
  background: var(--bg-root);
  color: var(--text-primary);
  overflow: hidden;
}

/* ═══════ Sidebar ═══════ */
.sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}
.brand-logo {
  width: 36px; height: 36px;
  flex-shrink: 0;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(99,102,241,0.3);
}
.brand-logo svg { width: 100%; height: 100%; display: block; }
.sidebar-brand h2 { font-size: 15px; font-weight: 700; color: var(--text-primary); line-height: 1.3; }
.sidebar-brand p  { font-size: 11px; color: var(--text-tertiary); }

.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  cursor: pointer;
  transition: all var(--duration-fast) ease;
  text-align: left;
  width: 100%;
}
.nav-item:hover {
  background: rgba(255,255,255,0.04);
  color: var(--text-primary);
}
.nav-item.active {
  background: rgba(99,102,241,0.12);
  color: #C7D2FE;
}
.nav-icon {
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.nav-icon :deep(svg) { width: 18px; height: 18px; }
.nav-indicator {
  position: absolute;
  right: 12px;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #818CF8;
  box-shadow: 0 0 8px rgba(129,140,248,0.5);
}

.sidebar-footer {
  padding: 14px 20px;
  border-top: 1px solid var(--border-subtle);
}
.ws-status {
  display: flex; align-items: center; gap: 8px;
  font-size: var(--font-size-xs); color: var(--text-tertiary);
}
.ws-dot {
  width: 7px; height: 7px; border-radius: 50%;
}
.ws-dot.on  { background: #34D399; box-shadow: 0 0 6px rgba(52,211,153,0.5); }
.ws-dot.off { background: #F87171; box-shadow: 0 0 6px rgba(248,113,113,0.5); }

/* ═══════ Main area ═══════ */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ── Top bar ── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.top-left { display: flex; align-items: baseline; gap: 16px; }
.top-left h1 { font-size: var(--font-size-lg); font-weight: 700; }
.top-time { font-size: var(--font-size-xs); color: var(--text-tertiary); font-family: var(--font-mono); }
.top-right { display: flex; align-items: center; gap: 10px; }
.header-actions { display: flex; gap: 6px; }
.logout-btn { color: #F87171 !important; border-color: rgba(239,68,68,0.2) !important; }
.logout-btn:hover { background: rgba(239,68,68,0.1) !important; color: #FCA5A5 !important; }

/* ── Content scroll ── */
.content-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
.content-inner { padding: 24px 28px 40px; }

/* ═══════ Metrics row ═══════ */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

/* ═══════ Chart panels ═══════ */
.chart-row {
  display: grid;
  gap: 16px;
  margin-bottom: 24px;
}
.chart-row.cols-2 { grid-template-columns: repeat(2, 1fr); }
.chart-row.cols-3 { grid-template-columns: repeat(3, 1fr); }

.chart-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color 0.3s ease;
}
.chart-panel:hover { border-color: var(--border-default); }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 0;
}
.panel-header h3 {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
}
.panel-badge {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  background: rgba(255,255,255,0.04);
  padding: 3px 10px;
  border-radius: 99px;
}
.panel-actions { display: flex; align-items: center; gap: 10px; }
.log-count { font-size: var(--font-size-xs); color: var(--text-tertiary); }

.panel-body { padding: 12px 20px 20px; }

.log-panel .panel-body { padding: 0 0 0 0; }
</style>

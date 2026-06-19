<template>
  <div class="dashboard">
    <!-- ═══ Sidebar ═══ -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 36 36" fill="none">
            <rect width="36" height="36" rx="10" fill="url(#side-logo-grad)"/>
            <path d="M10 26V12l8 8 8-8v14" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            <defs><linearGradient id="side-logo-grad" x1="0" y1="0" x2="36" y2="36"><stop stop-color="#E8784A"/><stop offset="1" stop-color="#F0A080"/></linearGradient></defs>
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
        <button @click="themeStore.toggle()" class="theme-toggle" :title="themeStore.mode === 'dark' ? '切换亮色模式' : '切换暗色模式'">
          <svg v-if="themeStore.mode === 'dark'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="10" r="4"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.93 4.93l1.41 1.41M13.66 13.66l1.41 1.41M4.93 15.07l1.41-1.41M13.66 6.34l1.41-1.41"/></svg>
          <svg v-else viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M17 12.5A7.5 7.5 0 017.5 3a7.5 7.5 0 109.5 9.5z"/></svg>
        </button>
      </div>
    </aside>

    <!-- ═══ Main content ═══ -->
    <div class="main-area">
      <!-- Header -->
      <header class="top-bar">
        <div class="top-left">
          <h1>{{ activeTabLabel }}</h1>
          <span class="top-time">{{ currentTime }}</span>
          <span class="top-freshness" v-if="dashboardStore.lastUpdate" :title="'数据更新于 ' + new Date(dashboardStore.lastUpdate).toLocaleTimeString()">
            <span class="fresh-dot"></span>
            {{ freshnessText }}
          </span>
        </div>
        <div class="top-right">
          <div class="header-actions">
            <button @click="toggleAutoPlay" :class="['btn', autoPlay ? 'btn-teal' : 'btn-ghost', 'btn-sm']" title="自动轮播">
              <svg viewBox="0 0 16 16" fill="currentColor" v-if="autoPlay"><rect x="4" y="3" width="3" height="10" rx="1"/><rect x="9" y="3" width="3" height="10" rx="1"/></svg>
              <svg viewBox="0 0 16 16" fill="currentColor" v-else><polygon points="5,3 14,8 5,13"/></svg>
              {{ autoPlay ? '暂停' : '轮播' }}
            </button>
            <a href="/query" class="btn btn-ghost btn-sm" v-if="canQuery" @click.prevent="navigateTo('/query')">查询管理</a>
            <a href="/admin" class="btn btn-ghost btn-sm" v-if="canAdmin" @click.prevent="navigateTo('/admin')">系统管理</a>
          </div>
          <button @click="handleLogout" class="btn btn-ghost btn-sm logout-btn">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M6 14H3.3A1.3 1.3 0 012 12.7V3.3A1.3 1.3 0 013.3 2H6M11 11l3-3-3-3M14 8H6"/></svg>
            退出
          </button>
        </div>
      </header>

      <!-- ═══ Global metrics bar (always visible) ═══ -->
      <div class="global-metrics" v-if="dataReady">
        <div :class="['g-metric', { 'g-anomaly': dashboardStore.anomalies.userSpike }]" style="--accent: var(--color-primary)">
          <span class="g-value"><AnimatedNumber :value="dashboardStore.metrics.onlineUsers" /></span>
          <span class="g-label">在线用户</span>
          <span :class="['g-trend', dashboardStore.metricsTrend.onlineUsers.type]">{{ dashboardStore.metricsTrend.onlineUsers.value }}</span>
        </div>
        <div class="g-divider"></div>
        <div class="g-metric" style="--accent: var(--color-teal)">
          <span class="g-value"><AnimatedNumber :value="dashboardStore.metrics.todayRecommendations" /></span>
          <span class="g-label">今日推荐</span>
          <span :class="['g-trend', dashboardStore.metricsTrend.todayRecommendations.type]">{{ dashboardStore.metricsTrend.todayRecommendations.value }}</span>
        </div>
        <div class="g-divider"></div>
        <div :class="['g-metric', { 'g-anomaly': dashboardStore.anomalies.ctrDrop }]" style="--accent: var(--color-indigo)">
          <span class="g-value"><AnimatedNumber :value="dashboardStore.metrics.todayCTR * 100" :decimals="2" />%</span>
          <span class="g-label">今日 CTR</span>
          <span :class="['g-trend', dashboardStore.metricsTrend.todayCTR.type]">{{ dashboardStore.metricsTrend.todayCTR.value }}</span>
        </div>
        <div class="g-divider"></div>
        <div class="g-metric" style="--accent: var(--color-amber)">
          <span class="g-value">{{ formatDuration(dashboardStore.metrics.avgWatchDuration) }}</span>
          <span class="g-label">人均时长</span>
          <span :class="['g-trend', dashboardStore.metricsTrend.avgWatchDuration.type]">{{ dashboardStore.metricsTrend.avgWatchDuration.value }}</span>
        </div>
        <div class="g-divider"></div>
        <div class="g-metric" style="--accent: var(--color-gold)">
          <span class="g-value"><AnimatedNumber :value="dashboardStore.metrics.coverage * 100" :decimals="1" />%</span>
          <span class="g-label">覆盖率</span>
          <span :class="['g-trend', dashboardStore.metricsTrend.coverage.type]">{{ dashboardStore.metricsTrend.coverage.value }}</span>
        </div>
      </div>

      <!-- Content scroll area -->
      <div class="content-scroll">
        <div class="content-inner">
          <!-- Loading skeleton -->
          <template v-if="!dataReady">
            <div class="metrics-row">
              <SkeletonCard v-for="i in 4" :key="'sm'+i" />
            </div>
            <div class="chart-row cols-2">
              <SkeletonChart v-for="i in 2" :key="'sc1'+i" />
            </div>
            <div class="chart-row cols-2">
              <SkeletonChart v-for="i in 2" :key="'sc2'+i" />
            </div>
          </template>

          <!-- ════════════════════════════════════════════ -->
          <!-- Tab 1: 实时概览 -->
          <!-- ════════════════════════════════════════════ -->
          <template v-if="activeTab === 'realtime' && dataReady">
            <div class="stagger">
              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>区域活跃热力图</h3><span class="panel-badge">24 小时分布</span></div>
                  <div class="panel-body"><RegionHeatmap :data="dashboardStore.regionData" /></div>
                </div>
                <div class="chart-panel log-panel">
                  <div class="panel-header">
                    <h3>实时行为日志</h3>
                    <div class="panel-actions">
                      <span class="log-count">{{ dashboardStore.eventLogs.length }} 条</span>
                      <button @click="dashboardStore.clearEventLogs" class="btn btn-ghost btn-sm">清空</button>
                    </div>
                  </div>
                  <div class="panel-body"><ScrollLog :logs="dashboardStore.eventLogs" @user-click="openUserProfile" /></div>
                </div>
              </div>

              <div class="chart-row cols-1">
                <div class="chart-panel">
                  <div class="panel-header"><h3>推荐内容</h3><span class="panel-badge">实时 Top 7</span></div>
                  <div class="panel-body">
                    <ContentCardGrid :items="dashboardStore.hotContent.slice(0, 7)" @item-click="openContentDetail" />
                  </div>
                </div>
              </div>

              <div class="chart-row cols-1">
                <div class="chart-panel">
                  <div class="panel-header"><h3>内容热度 Top 10</h3><span class="panel-badge">实时更新</span></div>
                  <div class="panel-body"><HotBarChart :data="dashboardStore.hotContent" @item-click="openContentDetail" /></div>
                </div>
              </div>
            </div>
          </template>

          <!-- ════════════════════════════════════════════ -->
          <!-- Tab 2: 效果分析 -->
          <!-- ════════════════════════════════════════════ -->
          <template v-if="activeTab === 'effect' && dataReady">
            <div class="stagger">
              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>CTR 趋势</h3><span class="panel-badge">近 7 天</span></div>
                  <div class="panel-body"><TrendLineChart :data="dashboardStore.trendData.ctr" /></div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>推荐曝光量趋势</h3><span class="panel-badge">近 7 天</span></div>
                  <div class="panel-body"><TrendLineChart :data="dashboardStore.trendData.playCount" /></div>
                </div>
              </div>

              <div class="chart-row cols-3">
                <div class="chart-panel">
                  <div class="panel-header"><h3>音乐 / 视频占比</h3></div>
                  <div class="panel-body">
                    <DonutChart :data="[{ name: '音乐', value: dashboardStore.musicVideoRatio.music }, { name: '视频', value: dashboardStore.musicVideoRatio.video }]" />
                  </div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>地区分布</h3></div>
                  <div class="panel-body">
                    <DonutChart :data="dashboardStore.regionDistribution.length ? dashboardStore.regionDistribution : [{ name: '暂无数据', value: 1 }]" />
                  </div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>推荐策略分布</h3></div>
                  <div class="panel-body">
                    <DonutChart :data="dashboardStore.strategyDistribution.length ? dashboardStore.strategyDistribution : [{ name: '暂无数据', value: 1 }]" />
                  </div>
                </div>
              </div>

              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>冷启动 vs 存量策略对比</h3><span class="panel-badge">CTR / CVR / 人均时长</span></div>
                  <div class="panel-body"><StrategyCompareChart :data="dashboardStore.compareData" /></div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>活跃用户 Top 10</h3><span class="panel-badge">播放 / 互动</span></div>
                  <div class="panel-body" style="padding:0;max-height:300px;overflow-y:auto">
                    <table class="user-rank-table" v-if="dashboardStore.activeUsers.length">
                      <thead><tr><th>#</th><th>用户ID</th><th>播放</th><th>互动率</th><th>冷启</th></tr></thead>
                      <tbody>
                        <tr v-for="(u, i) in dashboardStore.activeUsers" :key="u.user_id" @click="openUserProfile(u.user_id)" class="rank-row">
                          <td class="rank-num">{{ i + 1 }}</td>
                          <td class="rank-id">用户{{ u.user_id }}</td>
                          <td>{{ u.play_count }}</td>
                          <td>{{ ((u.like_rate + u.favorite_rate) * 100).toFixed(0) }}%</td>
                          <td><span :class="['badge', u.is_cold_start ? 'badge-amber' : 'badge-teal']">{{ u.is_cold_start ? '冷启' : '存量' }}</span></td>
                        </tr>
                      </tbody>
                    </table>
                    <div v-else class="empty-state" style="padding:32px"><p>暂无活跃用户数据</p></div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- ════════════════════════════════════════════ -->
          <!-- Tab 3: 冷启动分析 -->
          <!-- ════════════════════════════════════════════ -->
          <template v-if="activeTab === 'coldstart' && dataReady">
            <div class="stagger">
              <div class="metrics-row">
                <MetricCard title="冷启动用户数" :value="dashboardStore.coldstartStats.newUsers" unit="人" :trend="dashboardStore.coldstartStats.trends?.new_users?.value || ''" :trendType="dashboardStore.coldstartStats.trends?.new_users?.type || 'up'" accent="coral" icon="users" />
                <MetricCard title="聚类数量" :value="dashboardStore.clusterDistribution.length" unit="个" trend="" trendType="up" accent="teal" icon="target" />
                <MetricCard title="平均行为次数" :value="dashboardStore.coldstartStats.avgBehaviors" unit="次" :trend="dashboardStore.coldstartStats.trends?.avg_behavior_count?.value || ''" :trendType="dashboardStore.coldstartStats.trends?.avg_behavior_count?.type || 'up'" accent="indigo" icon="trend" />
                <MetricCard title="冷启动转化率" :value="dashboardStore.coldstartStats.conversionRate + '%'" unit="" :trend="dashboardStore.coldstartStats.trends?.conversion_rate?.value || ''" :trendType="dashboardStore.coldstartStats.trends?.conversion_rate?.type || 'up'" accent="amber" icon="clock" />
              </div>
              <div class="chart-row cols-2">
                <div class="chart-panel">
                  <div class="panel-header"><h3>冷启动用户聚类分布</h3></div>
                  <div class="panel-body"><ClusterPieChart :data="dashboardStore.clusterDistribution" /></div>
                </div>
                <div class="chart-panel">
                  <div class="panel-header"><h3>冷启动转化漏斗</h3></div>
                  <div class="panel-body"><FunnelChart :data="dashboardStore.funnelData" /></div>
                </div>
              </div>
            </div>
          </template>

        </div>
      </div>
    </div>

    <!-- Content Detail Modal -->
    <teleport to="body">
      <transition name="modal">
        <div v-if="contentModal.visible" class="modal-overlay" @click.self="closeContentModal">
          <div class="modal-card content-detail-card">
            <div class="modal-header">
              <h3>{{ contentModal.data?.title || '内容详情' }}</h3>
              <button @click="closeContentModal" class="modal-close">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 5l10 10M15 5L5 15"/></svg>
              </button>
            </div>
            <div class="modal-body" v-if="contentModal.data">
              <div class="detail-grid">
                <div class="detail-item"><span class="detail-label">ID</span><span class="detail-value">{{ contentModal.data.content_id }}</span></div>
                <div class="detail-item"><span class="detail-label">类型</span><span class="detail-value">{{ contentModal.data.content_type === 'music' ? '音乐' : '视频' }}</span></div>
                <div class="detail-item"><span class="detail-label">作者/艺人</span><span class="detail-value">{{ contentModal.data.artist_or_author || '-' }}</span></div>
                <div class="detail-item"><span class="detail-label">风格/分类</span><span class="detail-value">{{ contentModal.data.style_or_category || '-' }}</span></div>
                <div class="detail-item"><span class="detail-label">时长</span><span class="detail-value">{{ contentModal.data.duration ? (contentModal.data.duration + ' 秒') : '-' }}</span></div>
                <div class="detail-item"><span class="detail-label">语言</span><span class="detail-value">{{ contentModal.data.language || '-' }}</span></div>
                <div class="detail-item" v-if="contentModal.data.content_type === 'music'"><span class="detail-label">BPM</span><span class="detail-value">{{ contentModal.data.bpm || '-' }}</span></div>
              </div>
              <div class="detail-tags" v-if="contentModal.data.tags">
                <span class="detail-label">标签</span>
                <div class="tags-list">
                  <span v-for="tag in parseTags(contentModal.data.tags)" :key="tag" class="badge badge-coral" style="margin:3px">{{ tag }}</span>
                </div>
              </div>
              <div class="detail-footer">
                <router-link :to="`/content/${contentModal.data.content_id}?type=${contentModal.data.content_type || 'music'}`" class="btn btn-primary btn-sm">查看完整详情 →</router-link>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useDashboardStore } from "@/stores/dashboard";
import { useThemeStore } from "@/stores/theme";
import { useWebSocket } from "@/composables/useWebSocket";
import MetricCard from "./components/MetricCard.vue";
import SkeletonCard from "@/components/common/SkeletonCard.vue";
import SkeletonChart from "@/components/common/SkeletonChart.vue";
import TrendLineChart from "./components/TrendLineChart.vue";
import HotBarChart from "./components/HotBarChart.vue";
import DonutChart from "./components/DonutChart.vue";
import ClusterPieChart from "./components/ClusterPieChart.vue";
import FunnelChart from "./components/FunnelChart.vue";
import RegionHeatmap from "./components/RegionHeatmap.vue";
import ScrollLog from "./components/ScrollLog.vue";
import StrategyCompareChart from "./components/StrategyCompareChart.vue";
import ContentCardGrid from "./components/ContentCardGrid.vue";
import AnimatedNumber from "@/components/common/AnimatedNumber.vue";

const router = useRouter();
const authStore = useAuthStore();
const dashboardStore = useDashboardStore();
const themeStore = useThemeStore();
const { connected: wsConnected, connect: wsConnect, on: wsOn, off: wsOff } = useWebSocket();

const activeTab = ref("realtime");
const currentTime = ref("");
const dataReady = ref(false);
const autoPlay = ref(false);
let autoPlayTimer = null;

const tabOrder = ["realtime", "effect", "coldstart"];

function toggleAutoPlay() {
  autoPlay.value = !autoPlay.value;
  if (autoPlay.value) {
    autoPlayTimer = setInterval(() => {
      const idx = tabOrder.indexOf(activeTab.value);
      activeTab.value = tabOrder[(idx + 1) % tabOrder.length];
    }, 12000);
  } else {
    clearInterval(autoPlayTimer);
    autoPlayTimer = null;
  }
}

const canQuery = computed(() => authStore.hasRole("operator") || authStore.hasRole("admin"));
const canAdmin = computed(() => authStore.hasRole("admin"));

function navigateTo(path) {
  router.push(path).catch(() => {
    window.location.href = path;
  });
}

const tabs = [
  { id: "realtime", name: "实时概览", icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l3 2"/></svg>' },
  { id: "effect", name: "效果分析", icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 18L8 10l4 4 6-8"/><path d="M14 6h4v4"/></svg>' },
  { id: "coldstart", name: "冷启动分析", icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="10" r="8"/><path d="M10 2v4M10 14v4M2 10h4M14 10h4"/></svg>' },
];

const activeTabLabel = computed(() => tabs.find(t => t.id === activeTab.value)?.name || "");

const freshnessText = ref("");
let freshnessTimer = null;

function updateFreshness() {
  if (!dashboardStore.lastUpdate) { freshnessText.value = ""; return; }
  const sec = Math.floor((Date.now() - dashboardStore.lastUpdate) / 1000);
  freshnessText.value = sec < 5 ? "实时" : sec < 60 ? `${sec}秒前` : `${Math.floor(sec / 60)}分钟前`;
}


function formatDuration(seconds) {
  if (!seconds) return "00:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

const contentModal = reactive({ visible: false, data: null });

async function openContentDetail(item) {
  try {
    const token = localStorage.getItem("accessToken");
    const typeParam = item.content_type ? `?type=${item.content_type}` : "";
    const resp = await fetch(`/api/content/${item.content_id}${typeParam}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      const json = await resp.json();
      contentModal.data = json.data;
      contentModal.visible = true;
    }
  } catch (e) {
    console.error("Failed to load content detail:", e);
  }
}

function closeContentModal() {
  contentModal.visible = false;
  contentModal.data = null;
}

function openUserProfile(userId) {
  if (!userId) return;
  router.push(`/query/user/${userId}`);
}

function parseTags(tags) {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags;
  try { return JSON.parse(tags); } catch { return []; }
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
let onDashboardUpdate = null;
let onUserEvent = null;

const TODAY = () => new Date().toISOString().split("T")[0];

onMounted(async () => {
  updateTime();
  timeInterval = setInterval(updateTime, 1000);
  freshnessTimer = setInterval(updateFreshness, 1000);

  try {
    await Promise.all([
      dashboardStore.loadMetrics(),
      dashboardStore.loadTrendData(),
      dashboardStore.loadHotContent(),
      dashboardStore.loadColdstartAnalysis(),
      dashboardStore.loadRegionData(),
    ]);
  } catch (e) {
    console.error("Initial data load failed:", e.message);
  } finally {
    dataReady.value = true;
  }

  wsConnect();

  onDashboardUpdate = (msg) => {
    if (!msg || msg.type !== "dashboard_snapshot") return;
    const d = msg.data;
    if (!d) return;
    if (d.data_date && d.data_date !== TODAY()) return;
    dashboardStore.applySnapshot(d);
  };

  onUserEvent = (msg) => {
    const d = msg?.data;
    if (d) {
      dashboardStore.addEventLog({
        user_id: d.user_id || 0,
        event_type: d.event_type || "未知",
        content_type: d.content_type || "音乐",
        content_id: d.content_id || 0,
        content_title: d.content_title || "",
        content_artist: d.content_artist || "",
      });
    }
  };

  wsOn("dashboard_update", onDashboardUpdate);
  wsOn("user_event", onUserEvent);
});

onUnmounted(() => {
  clearInterval(timeInterval);
  clearInterval(freshnessTimer);
  clearInterval(autoPlayTimer);
  wsOff("dashboard_update", onDashboardUpdate);
  wsOff("user_event", onUserEvent);
});
</script>

<style scoped>
.dashboard {
  display: flex; height: 100vh;
  background:
    radial-gradient(ellipse 80% 50% at 80% 0%, rgba(232,120,74,0.06), transparent),
    radial-gradient(ellipse 60% 40% at 20% 100%, rgba(245,158,11,0.04), transparent),
    var(--bg-root);
  color: var(--text-primary); overflow: hidden;
}

/* ═══════ Sidebar ═══════ */
.sidebar {
  width: 220px; flex-shrink: 0; display: flex; flex-direction: column;
  background: linear-gradient(180deg, #FFF9F4 0%, #FFF3EA 50%, #FFEDE0 100%);
  border-right: 1px solid var(--border-subtle);
}
.sidebar-brand {
  display: flex; align-items: center; gap: 12px;
  padding: 22px 20px 20px;
  background: linear-gradient(180deg, rgba(232,120,74,0.06), transparent);
  border-bottom: 1px solid var(--border-subtle);
}
.brand-logo {
  width: 38px; height: 38px; flex-shrink: 0; border-radius: 10px;
  box-shadow: 0 4px 16px rgba(232,120,74,0.3);
}
.brand-logo svg { width: 100%; height: 100%; display: block; }
.sidebar-brand h2 { font-size: 15px; font-weight: 700; background: linear-gradient(135deg, var(--color-primary-dark), var(--color-amber-dark)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.sidebar-brand p { font-size: 11px; color: var(--text-tertiary); }

.sidebar-nav { flex: 1; padding: 16px 10px; display: flex; flex-direction: column; gap: 4px; }

.nav-item {
  position: relative; display: flex; align-items: center; gap: 10px;
  padding: 11px 14px; border: none; border-radius: var(--radius-md);
  background: transparent; color: var(--text-secondary);
  font-size: var(--font-size-sm); font-family: var(--font-family);
  cursor: pointer; transition: all var(--duration-fast) ease;
  text-align: left; width: 100%;
}
.nav-item:hover { background: rgba(232,120,74,0.08); color: var(--text-primary); }
.nav-item.active {
  background: linear-gradient(135deg, rgba(232,120,74,0.14), rgba(245,158,11,0.08));
  color: var(--color-primary-dark); font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(232,120,74,0.15);
}
.nav-icon { width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.nav-icon :deep(svg) { width: 18px; height: 18px; }
.nav-indicator {
  position: absolute; right: 12px; width: 6px; height: 6px; border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-amber));
  box-shadow: 0 0 10px var(--color-amber-glow);
}

.sidebar-footer { padding: 14px 20px; border-top: 1px solid var(--border-subtle); }
.ws-status { display: flex; align-items: center; gap: 8px; font-size: var(--font-size-xs); color: var(--text-tertiary); }
.ws-dot { width: 8px; height: 8px; border-radius: 50%; }
.ws-dot.on  { background: linear-gradient(135deg, #34D399, #2D9D7A); box-shadow: 0 0 8px rgba(52,211,153,0.6); }
.ws-dot.off { background: linear-gradient(135deg, #F87171, #E0554A); box-shadow: 0 0 8px rgba(248,113,113,0.6); }

.theme-toggle {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(180,130,100,0.06); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); color: var(--text-secondary); cursor: pointer;
  transition: all var(--duration-fast);
  margin-top: 8px;
}
.theme-toggle:hover { background: rgba(232,120,74,0.12); color: var(--color-primary-dark); border-color: var(--border-default); }
.theme-toggle :deep(svg) { width: 16px; height: 16px; }

/* ═══════ Main area ═══════ */
.main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; }

/* ── Top bar ── */
.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 28px;
  background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,248,243,0.9));
  border-bottom: 1px solid var(--border-subtle); flex-shrink: 0;
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}
.top-left { display: flex; align-items: baseline; gap: 16px; }
.top-left h1 {
  font-size: var(--font-size-lg); font-weight: 700;
  background: linear-gradient(135deg, var(--text-primary), var(--color-bronze-dark));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.top-time { font-size: var(--font-size-xs); color: var(--text-tertiary); font-family: var(--font-mono); }
.top-right { display: flex; align-items: center; gap: 10px; }
.header-actions { display: flex; gap: 6px; }
.logout-btn { color: var(--color-rose) !important; border-color: rgba(240,98,110,0.2) !important; }
.logout-btn:hover { background: rgba(240,98,110,0.08) !important; color: var(--color-rose-dark) !important; }

/* ═══════ Global metrics bar ═══════ */
.global-metrics {
  display: flex; align-items: center; gap: 0;
  padding: 10px 28px; flex-shrink: 0;
  background: linear-gradient(180deg, rgba(255,255,255,0.7), rgba(255,248,243,0.5));
  border-bottom: 1px solid var(--border-subtle);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
}
.g-metric {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}
.g-metric:hover { background: rgba(232,120,74,0.04); }
.g-value {
  font-size: var(--font-size-xl); font-weight: 800;
  color: var(--text-primary); font-family: var(--font-mono);
  line-height: 1;
}
.g-label {
  font-size: 11px; color: var(--text-tertiary);
  letter-spacing: 0.03em; font-weight: 500;
}
.g-trend {
  font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 99px;
}
.g-trend.up   { color: var(--color-teal); background: rgba(45,157,122,0.08); }
.g-trend.down { color: var(--color-rose); background: rgba(240,98,110,0.08); }
.g-trend:empty { display: none; }

.g-divider {
  width: 1px; height: 32px;
  background: linear-gradient(180deg, transparent, var(--border-default), transparent);
  margin: 0 12px;
}

.g-anomaly {
  animation: anomaly-pulse 1.5s ease-in-out infinite;
  border-radius: var(--radius-md);
  background: rgba(240, 98, 110, 0.06);
}

@keyframes anomaly-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(240, 98, 110, 0); }
  50%      { box-shadow: 0 0 0 4px rgba(240, 98, 110, 0.2); }
}

/* ── Freshness indicator ── */
.top-freshness {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: var(--text-tertiary);
  background: rgba(180,130,100,0.05); padding: 2px 10px; border-radius: 99px;
}
.fresh-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #34D399; box-shadow: 0 0 6px rgba(52,211,153,0.5);
}

/* ── User rank table ── */
.user-rank-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.user-rank-table thead { background: linear-gradient(180deg, rgba(232,120,74,0.06), transparent); }
.user-rank-table thead th {
  padding: 10px 14px; text-align: left;
  font-size: 11px; font-weight: 600; color: var(--color-bronze-dark);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.user-rank-table tbody td { padding: 9px 14px; border-bottom: 1px solid var(--border-subtle); }
.rank-row { cursor: pointer; transition: background var(--duration-fast); }
.rank-row:hover { background: rgba(232,120,74,0.05); }
.rank-num { font-family: var(--font-mono); font-weight: 700; color: var(--color-primary); }
.rank-id { color: var(--color-primary); font-weight: 500; }
.rank-id:hover { text-decoration: underline; }

/* ── Content ── */
.content-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; }
.content-inner { padding: 24px 28px 48px; }

/* ═══════ Metrics row ═══════ */
.metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }

/* ═══════ Chart panels ═══════ */
.chart-row { display: grid; gap: 18px; margin-bottom: 24px; }
.chart-row.cols-1 { grid-template-columns: 1fr; }
.chart-row.cols-2 { grid-template-columns: repeat(2, 1fr); }
.chart-row.cols-3 { grid-template-columns: repeat(3, 1fr); }

.chart-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  overflow: hidden;
  transition: all var(--duration-normal) ease;
  box-shadow: var(--shadow-sm);
}
.chart-panel:hover {
  border-color: var(--border-default);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 22px 12px;
  border-bottom: 1px solid var(--border-subtle);
  background: linear-gradient(180deg, rgba(255,248,243,0.4), transparent);
}
.panel-header h3 { font-size: var(--font-size-base); font-weight: 700; color: var(--text-primary); }
.panel-badge {
  font-size: var(--font-size-xs); color: var(--color-bronze);
  background: linear-gradient(135deg, rgba(232,120,74,0.08), rgba(245,158,11,0.05));
  padding: 3px 12px; border-radius: 99px; font-weight: 500;
  border: 1px solid var(--border-subtle);
}
.panel-actions { display: flex; align-items: center; gap: 10px; }
.log-count { font-size: var(--font-size-xs); color: var(--text-tertiary); }
.panel-body { padding: 16px 22px 22px; }
.log-panel .panel-body { padding: 0; }

/* ── Content detail modal ── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  display: flex; align-items: center; justify-content: center;
  background: rgba(40,20,10,0.45); backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.modal-card {
  width: 480px; max-width: 94vw;
  background: linear-gradient(180deg, var(--bg-surface), var(--bg-surface-warm));
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-xl);
  box-shadow: 0 24px 64px rgba(120,80,50,0.18);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 22px 26px 0;
}
.modal-header h3 { font-size: var(--font-size-lg); font-weight: 700; }
.modal-close {
  width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;
  background: rgba(232,120,74,0.06); border: 1px solid var(--border-subtle);
  border-radius: 8px; color: var(--text-secondary); cursor: pointer;
  transition: all var(--duration-fast);
}
.modal-close:hover { background: rgba(232,120,74,0.12); color: var(--text-primary); border-color: var(--border-default); }
.modal-close svg { width: 16px; height: 16px; }
.modal-body { padding: 16px 26px 24px; }
.modal-enter-active { transition: opacity 0.25s ease; }
.modal-enter-active .modal-card { animation: fadeInScale 0.3s cubic-bezier(0.19,1,0.22,1); }
.modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }

.content-detail-card .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.detail-item { display: flex; flex-direction: column; gap: 2px; }
.detail-label { font-size: var(--font-size-xs); color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
.detail-value { font-size: var(--font-size-sm); color: var(--text-primary); font-weight: 500; }
.detail-tags { margin-top: 18px; }
.detail-tags .detail-label { display: block; margin-bottom: 8px; }
.detail-footer { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-subtle); }
.tags-list { display: flex; flex-wrap: wrap; gap: 6px; }
</style>

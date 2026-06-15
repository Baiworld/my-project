import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/api";

// ═══════════════════════════════════════════════════════════════
// 数据契约层 — 所有数据入口归一化，杜绝字段名不一致
// ═══════════════════════════════════════════════════════════════

/** 后端 WebSocket 推送 snake_case → 前端 camelCase 映射 */
function _snakeVal(obj, snake, camel, fallback) {
  // 优先 snake_case（WebSocket），其次 camelCase（API），最后 fallback
  if (obj[snake] != null) return obj[snake];
  if (obj[camel] != null) return obj[camel];
  return fallback;
}

function _trend(val) {
  if (val && typeof val.value === "string") return val;
  return { value: String(val?.value ?? ""), type: val?.type ?? "up" };
}

/**
 * WebSocket 快照 → Store 规范格式
 * 所有字段名映射只在此函数中维护，模板和 handler 不再做 ad-hoc 转换。
 */
function normalizeSnapshot(d) {
  const trend = (snake, camel) => _snakeVal(d?.metrics_trend || {}, snake, camel, null);

  return {
    metrics: {
      onlineUsers: _snakeVal(d, "online_users", "onlineUsers", 0),
      todayRecommendations: _snakeVal(d, "daily_recommendations", "todayRecommendations", 0),
      todayCTR: _snakeVal(d, "ctr", "todayCTR", 0),
      avgWatchDuration: _snakeVal(d, "avg_watch_duration", "avgWatchDuration", 0),
      coverage: _snakeVal(d, "coverage", "coverage", 0),
    },
    metricsTrend: {
      onlineUsers: _trend(trend("online_users", "onlineUsers")),
      todayRecommendations: _trend(trend("daily_recommendations", "todayRecommendations")),
      todayCTR: _trend(trend("ctr", "todayCTR")),
      avgWatchDuration: _trend(trend("avg_watch_duration", "avgWatchDuration")),
      coverage: _trend(trend("coverage", "coverage")),
    },
    trendData: {
      ctr: d.ctr_trend ?? [],
      playCount: d.play_count_trend ?? [],
    },
    coldstartStats: {
      newUsers: _snakeVal(d.coldstart_stats || {}, "new_users", "newUsers", 0),
      conversionRate: _snakeVal(d.coldstart_stats || {}, "conversion_rate", "conversionRate", 0),
      avgBehaviors: _snakeVal(d.coldstart_stats || {}, "avg_behavior_count", "avgBehaviors", 0),
      trends: {
        new_users: _trend((d.coldstart_stats?.trends || {}).new_users),
        conversion_rate: _trend((d.coldstart_stats?.trends || {}).conversion_rate),
        avg_behavior_count: _trend((d.coldstart_stats?.trends || {}).avg_behavior_count),
      },
    },
    funnelData: d.funnel_data ?? [],
    compareData: {
      coldstart: d.compare_data?.coldstart ?? {},
      existing: d.compare_data?.existing ?? {},
    },
    hotContent: d.hot_content_top5 ?? [],
    clusterDistribution: d.cluster_distribution ?? [],
    strategyDistribution: d.strategy_distribution ?? [],
    contentRatio: {
      music: d.content_ratio?.music ?? 0,
      video: d.content_ratio?.video ?? 0,
    },
  };
}


// ═══════════════════════════════════════════════════════════════
// Store
// ═══════════════════════════════════════════════════════════════

export const useDashboardStore = defineStore("dashboard", () => {
  const metrics = ref({
    onlineUsers: 0,
    todayRecommendations: 0,
    todayCTR: 0,
    avgWatchDuration: 0,
    coverage: 0,
  });

  const metricsTrend = ref({
    onlineUsers: { value: "", type: "up" },
    todayRecommendations: { value: "", type: "up" },
    todayCTR: { value: "", type: "up" },
    avgWatchDuration: { value: "", type: "up" },
    coverage: { value: "", type: "up" },
  });

  const trendData = ref({
    ctr: [],
    playCount: [],
  });

  const hotContent = ref([]);
  const clusterDistribution = ref([]);
  const coldstartStats = ref({
    newUsers: 0,
    conversionRate: 0,
    avgBehaviors: 0,
    trends: {
      new_users: { value: "", type: "up" },
      conversion_rate: { value: "", type: "up" },
      avg_behavior_count: { value: "", type: "up" },
    },
  });

  const funnelData = ref([]);
  const strategyDistribution = ref([]);
  const compareData = ref({ coldstart: {}, existing: {} });
  const regionData = ref([]);
  const eventLogs = ref([]);
  const contentRatio = ref({ music: 0, video: 0 });

  const musicVideoRatio = computed(() => {
    const music = contentRatio.value.music ?? hotContent.value.filter((c) => c.content_type === "music").length;
    const video = contentRatio.value.video ?? hotContent.value.filter((c) => c.content_type === "video").length;
    const total = (music + video) || 1;
    return {
      music: Math.round((music / total) * 100),
      video: Math.round((video / total) * 100),
    };
  });

  // ══════════════════════════════════════════════════════════
  // 数据入口
  // ══════════════════════════════════════════════════════════

  /** WebSocket 快照统一入口 — 一次调用更新全部 store 字段 */
  function applySnapshot(rawSnapshot) {
    const s = normalizeSnapshot(rawSnapshot);
    metrics.value = s.metrics;
    metricsTrend.value = s.metricsTrend;
    trendData.value = s.trendData;
    coldstartStats.value = s.coldstartStats;
    funnelData.value = s.funnelData;
    compareData.value = s.compareData;
    if (s.hotContent.length > 0) hotContent.value = s.hotContent;
    if (s.clusterDistribution.length > 0) clusterDistribution.value = s.clusterDistribution;
    if (s.strategyDistribution.length > 0) strategyDistribution.value = s.strategyDistribution;
    contentRatio.value = s.contentRatio;
  }

  async function loadMetrics() {
    try {
      const today = new Date();
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      const endStr = today.toISOString().split("T")[0];
      const startStr = weekAgo.toISOString().split("T")[0];

      const response = await api.metrics.get({ start_date: startStr, end_date: endStr });
      const payload = response.data.data;
      const pick = (d, ug, ct) => d.user_group === ug && d.content_type === ct;
      const sorted = [...payload].sort((a, b) => b.metric_date.localeCompare(a.metric_date));
      const todayRow = sorted.find((d) => pick(d, "all", "all"));
      const prevRow = sorted.filter((d) => pick(d, "all", "all"))[1];

      if (todayRow) {
        metrics.value = {
          onlineUsers: todayRow.total_users || 0,
          todayRecommendations: todayRow.total_impressions || 0,
          todayCTR: todayRow.ctr || 0,
          avgWatchDuration: todayRow.avg_watch_duration || 0,
          coverage: todayRow.coverage || 0,
        };
      }

      if (todayRow && prevRow) {
        metricsTrend.value = {
          onlineUsers: calcTrend(todayRow.total_users, prevRow.total_users),
          todayRecommendations: calcTrend(todayRow.total_impressions, prevRow.total_impressions),
          todayCTR: calcTrend(todayRow.ctr, prevRow.ctr),
          avgWatchDuration: calcTrend(todayRow.avg_watch_duration, prevRow.avg_watch_duration),
          coverage: calcTrend(todayRow.coverage, prevRow.coverage),
        };
      }

      const latestDate = sorted[0]?.metric_date;
      if (latestDate) {
        const csAll = payload.find((d) => d.metric_date === latestDate && pick(d, "coldstart", "all"));
        const exAll = payload.find((d) => d.metric_date === latestDate && pick(d, "existing", "all"));
        if (csAll || exAll) {
          compareData.value = {
            coldstart: csAll ? { ctr: csAll.ctr || 0, cvr: csAll.cvr || 0, avg_watch_duration: csAll.avg_watch_duration || 0 } : {},
            existing: exAll ? { ctr: exAll.ctr || 0, cvr: exAll.cvr || 0, avg_watch_duration: exAll.avg_watch_duration || 0 } : {},
          };
        }
      }

      if (todayRow) {
        funnelData.value = [
          { value: 100, name: "推荐曝光", itemStyle: { color: "#6366F1" } },
          { value: Math.max(1, Math.round(todayRow.ctr * 100)), name: "用户点击", itemStyle: { color: "#818CF8" } },
          { value: Math.max(1, Math.round(todayRow.cvr * 100)), name: "完播转化", itemStyle: { color: "#34D399" } },
          { value: Math.max(1, Math.round((todayRow.coldstart_conversion || 0) * 100)), name: "冷启活跃", itemStyle: { color: "#FBBF24" } },
        ];
      }
    } catch (error) {
      console.error("Failed to load metrics:", error);
    }
  }

  function calcTrend(current, previous) {
    if (!previous || previous === 0) return { value: "", type: "up" };
    const pct = ((current - previous) / previous) * 100;
    const sign = pct >= 0 ? "+" : "";
    return { value: `${sign}${pct.toFixed(1)}%`, type: pct >= 0 ? "up" : "down" };
  }

  async function loadTrendData(days = 7) {
    try {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      const response = await api.metrics.get({
        start_date: startDate.toISOString().split("T")[0],
        end_date: endDate.toISOString().split("T")[0],
      });
      const trendAll = response.data.data.filter(
        (d) => d.user_group === "all" && d.content_type === "all"
      );
      trendData.value = {
        ctr: trendAll.map((d) => ({ date: d.metric_date, value: d.ctr || 0 })),
        playCount: trendAll.map((d) => ({ date: d.metric_date, value: d.total_impressions || 0 })),
      };
    } catch (error) {
      console.error("Failed to load trend data:", error);
    }
  }

  async function loadHotContent() {
    try {
      const response = await api.content.getHot({ top_n: 10 });
      hotContent.value = response.data.data;
    } catch (error) {
      console.error("Failed to load hot content:", error);
    }
  }

  async function loadColdstartAnalysis() {
    try {
      const response = await api.coldstart.getStats();
      const csPayload = response.data.data;
      coldstartStats.value = {
        newUsers: csPayload.total_coldstart_users_24h || 0,
        conversionRate: csPayload.conversion_rate || 0,
        avgBehaviors: csPayload.avg_behavior_count || 0,
        trends: coldstartStats.value.trends,
      };
      clusterDistribution.value = csPayload.cluster_distribution || [];
      if (csPayload.strategy_distribution?.length > 0) {
        strategyDistribution.value = csPayload.strategy_distribution;
      }
    } catch (error) {
      console.error("Failed to load coldstart analysis:", error);
    }
  }

  async function loadRegionData() {
    try {
      const response = await api.region.getHeatmap();
      regionData.value = response.data.data?.points || [];
    } catch (error) {
      console.error("Failed to load region data:", error);
    }
  }

  function addEventLog(log) {
    eventLogs.value.unshift({ ...log, timestamp: new Date().toLocaleTimeString() });
    if (eventLogs.value.length > 50) eventLogs.value.pop();
  }

  function clearEventLogs() {
    eventLogs.value = [];
  }

  return {
    metrics, metricsTrend, trendData, hotContent, clusterDistribution,
    coldstartStats, funnelData, strategyDistribution, compareData,
    regionData, eventLogs, contentRatio, musicVideoRatio,
    applySnapshot, loadMetrics, loadTrendData, loadHotContent,
    loadColdstartAnalysis, loadRegionData, addEventLog, clearEventLogs,
  };
});

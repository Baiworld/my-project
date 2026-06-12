import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/api";

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
  });

  const funnelData = ref([]);

  const strategyDistribution = ref([]);
  const compareData = ref({ coldstart: {}, existing: {} });

  const regionData = ref([]);

  const eventLogs = ref([]);

  const musicVideoRatio = computed(() => {
    const music = hotContent.value.filter((c) => c.content_type === "music").length;
    const video = hotContent.value.filter((c) => c.content_type === "video").length;
    const total = music + video || 1;
    return {
      music: Math.round((music / total) * 100),
      video: Math.round((video / total) * 100),
    };
  });

  async function loadMetrics() {
    try {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const dayBefore = new Date();
      dayBefore.setDate(dayBefore.getDate() - 2);
      const endStr = yesterday.toISOString().split("T")[0];
      const startStr = dayBefore.toISOString().split("T")[0];

      const response = await api.metrics.get({
        start_date: startStr,
        end_date: endStr,
      });
      const payload = response.data.data;
      const pick = (d, ug, ct) => d.user_group === ug && d.content_type === ct;

      const todayRow = payload.find((d) => pick(d, "all", "all"));
      const prevRow = payload.find((d) => d.metric_date === startStr && pick(d, "all", "all"));
      if (todayRow) {
        metrics.value = {
          onlineUsers: todayRow.total_users || 0,
          todayRecommendations: todayRow.total_impressions || 0,
          todayCTR: todayRow.ctr || 0,
          avgWatchDuration: todayRow.avg_watch_duration || 0,
          coverage: todayRow.coverage || 0,
        };
      }
      // Strategy comparison: latest day coldstart vs existing
      const csAll = payload.find((d) => d.metric_date === endStr && pick(d, "coldstart", "all"));
      const exAll = payload.find((d) => d.metric_date === endStr && pick(d, "existing", "all"));
      if (csAll || exAll) {
        compareData.value = {
          coldstart: csAll ? { ctr: csAll.ctr || 0, cvr: csAll.cvr || 0, avg_watch_duration: csAll.avg_watch_duration || 0 } : {},
          existing: exAll ? { ctr: exAll.ctr || 0, cvr: exAll.cvr || 0, avg_watch_duration: exAll.avg_watch_duration || 0 } : {},
        };
      }

      // Compute conversion funnel from the all/all row
      if (todayRow) {
        const imp = todayRow.total_impressions || 1;
        const clk = todayRow.total_clicks || 0;
        const cvr = todayRow.cvr || 0;
        const ctr = todayRow.ctr || 0;
        funnelData.value = [
          { value: 100, name: "推荐曝光", itemStyle: { color: "#6366F1" } },
          { value: Math.round(ctr * 100), name: "用户点击", itemStyle: { color: "#818CF8" } },
          { value: Math.round(cvr * 100), name: "完播转化", itemStyle: { color: "#34D399" } },
          { value: Math.round(todayRow.coldstart_conversion * 100 || 0), name: "冷启活跃", itemStyle: { color: "#FBBF24" } },
        ];
      }

      // Compute trends by comparing today vs previous day
      if (todayRow && prevRow) {
        metricsTrend.value = {
          onlineUsers: calcTrend(todayRow.total_users, prevRow.total_users),
          todayRecommendations: calcTrend(todayRow.total_impressions, prevRow.total_impressions),
          todayCTR: calcTrend(todayRow.ctr, prevRow.ctr),
          avgWatchDuration: calcTrend(todayRow.avg_watch_duration, prevRow.avg_watch_duration),
          coverage: calcTrend(todayRow.coverage, prevRow.coverage),
        };
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

      const trendPayload = response.data.data;
      const trendAll = trendPayload.filter((d) => d.user_group === "all" && d.content_type === "all");
      trendData.value = {
        ctr: trendAll.map((d) => ({
          date: d.metric_date,
          value: d.ctr || 0,
        })),
        playCount: trendAll.map((d) => ({
          date: d.metric_date,
          value: d.total_impressions || 0,
        })),
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
      };
      clusterDistribution.value = csPayload.cluster_distribution || [];
      if (csPayload.strategy_distribution && csPayload.strategy_distribution.length > 0) {
        strategyDistribution.value = csPayload.strategy_distribution;
      }
    } catch (error) {
      console.error("Failed to load coldstart analysis:", error);
    }
  }

  function addEventLog(log) {
    eventLogs.value.unshift({
      ...log,
      timestamp: new Date().toLocaleTimeString(),
    });
    if (eventLogs.value.length > 50) {
      eventLogs.value.pop();
    }
  }

  function clearEventLogs() {
    eventLogs.value = [];
  }

  return {
    metrics,
    metricsTrend,
    trendData,
    hotContent,
    clusterDistribution,
    coldstartStats,
    funnelData,
    strategyDistribution,
    compareData,
    regionData,
    eventLogs,
    musicVideoRatio,
    loadMetrics,
    loadTrendData,
    loadHotContent,
    loadColdstartAnalysis,
    addEventLog,
    clearEventLogs,
  };
});
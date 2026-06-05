import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/api";

export const useDashboardStore = defineStore("dashboard", () => {
  const metrics = ref({
    onlineUsers: 0,
    todayRecommendations: 0,
    todayCTR: 0,
    avgWatchDuration: 0,
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
  });

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
      const response = await api.metrics.get({
        start_date: new Date().toISOString().split("T")[0],
        end_date: new Date().toISOString().split("T")[0],
      });
      const payload = response.data.data;
      if (payload.length > 0) {
        const latest = payload[0];
        metrics.value = {
          onlineUsers: latest.total_users || 0,
          todayRecommendations: latest.total_impressions || 0,
          todayCTR: latest.ctr || 0,
          avgWatchDuration: latest.avg_watch_duration || 0,
        };
      }
    } catch (error) {
      console.error("Failed to load metrics:", error);
    }
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
      trendData.value = {
        ctr: trendPayload.map((d) => ({
          date: d.metric_date,
          value: d.ctr || 0,
        })),
        playCount: trendPayload.map((d) => ({
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
      const response = await api.coldstart.getAnalysis();
      const csPayload = response.data.data;
      coldstartStats.value = {
        newUsers: csPayload.total_coldstart_users_24h || 0,
        conversionRate: 0,
      };
      clusterDistribution.value = csPayload.cluster_distribution || [];
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
    trendData,
    hotContent,
    clusterDistribution,
    coldstartStats,
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
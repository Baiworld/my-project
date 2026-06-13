<template>
  <div ref="chartRef" class="chart-box-sm"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Array, default: () => [] },
});

const chartRef = ref(null);
let chartInstance = null;

const colors = ["#E8784A", "#F0A080", "#E8A040", "#C88030", "#D08060", "#F5C0A0", "#B87050", "#A06040"];

function buildOption() {
  const clusterData = props.data.length
    ? props.data.map((d, i) => ({
        value: d.count || d.user_count || 0,
        name: d.cluster_name || `簇 ${d.cluster_id || i}`,
        itemStyle: { color: colors[i % colors.length] },
      }))
    : [{ value: 1, name: "暂无聚类数据", itemStyle: { color: colors[0] } }];

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(60, 40, 30, 0.9)",
      borderColor: "#D8C0B0",
      textStyle: { color: "#fff" },
    },
    series: [{
      type: "pie",
      radius: ["40%", "70%"],
      center: ["50%", "50%"],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: "#E8D8CC", borderWidth: 2 },
      label: { show: true, color: "#8B7268", fontSize: 10, formatter: "{b}\n{c}" },
      labelLine: { lineStyle: { color: "#C8B0A0" } },
      data: clusterData,
    }],
  };
}

function updateChart() {
  if (!chartInstance || !chartRef.value) return;
  chartInstance.setOption(buildOption());
}

function initChart() {
  if (!chartRef.value) return;
  chartInstance = echarts.init(chartRef.value);
  updateChart();
}

function handleResize() { chartInstance?.resize(); }

onMounted(() => {
  initChart();
  window.addEventListener("resize", handleResize);
});

watch(() => props.data, () => { updateChart(); }, { deep: true });

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});
</script>

<style scoped>
.chart-box-sm { width: 100%; height: 200px; }
</style>

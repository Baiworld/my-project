<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Array, default: () => [] },
});

const chartRef = ref(null);
let chartInstance = null;

function buildOption() {
  return {
    backgroundColor: "transparent",
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(60, 40, 30, 0.9)",
      borderColor: "#D8C0B0",
      textStyle: { color: "#fff" },
    },
    xAxis: {
      type: "category",
      data: props.data.map((d) => d.date),
      axisLine: { lineStyle: { color: "#C8B0A0" } },
      axisLabel: { color: "#8B7268", fontSize: 10 },
    },
    yAxis: {
      type: "value",
      axisLine: { lineStyle: { color: "#C8B0A0" } },
      axisLabel: { color: "#8B7268", fontSize: 10 },
      splitLine: { lineStyle: { color: "#D8C0B0" } },
    },
    series: [{
      name: "CTR",
      type: "line",
      smooth: true,
      data: props.data.map((d) => d.value),
      lineStyle: { color: "#E8784A", width: 3 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: "rgba(232,120,74,0.4)" },
          { offset: 1, color: "rgba(232,120,74,0.05)" },
        ]),
      },
      symbol: "circle",
      symbolSize: 6,
      itemStyle: { color: "#E8784A" },
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
.chart-box { width: 100%; height: 260px; }
</style>

<template>
  <div ref="chartRef" class="compare-chart"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Object, default: () => ({ coldstart: {}, existing: {} }) },
});

const chartRef = ref(null);
let chartInstance = null;

function buildOption() {
  const cs = props.data.coldstart || {};
  const ex = props.data.existing || {};

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(60,40,30,0.9)",
      borderColor: "#D8C0B0",
      textStyle: { color: "#fff" },
    },
    legend: {
      data: ["冷启动用户", "存量用户"],
      bottom: 0,
      textStyle: { color: "#8B7268", fontSize: 11 },
    },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: "category",
      data: ["CTR (%)", "CVR (%)", "人均播放(s)"],
      axisLabel: { color: "#8B7268", fontSize: 10 },
      axisLine: { lineStyle: { color: "#C8B0A0" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8B7268", fontSize: 10 },
      splitLine: { lineStyle: { color: "#D8C0B0" } },
    },
    series: [
      {
        name: "冷启动用户",
        type: "bar",
        data: [
          +(cs.ctr * 100 || 0).toFixed(1),
          +(cs.cvr * 100 || 0).toFixed(1),
          +(cs.avg_watch_duration || 0).toFixed(0),
        ],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
            { offset: 0, color: "#E8784A" },
            { offset: 1, color: "#F0A080" },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        barGap: "20%",
      },
      {
        name: "存量用户",
        type: "bar",
        data: [
          +(ex.ctr * 100 || 0).toFixed(1),
          +(ex.cvr * 100 || 0).toFixed(1),
          +(ex.avg_watch_duration || 0).toFixed(0),
        ],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
            { offset: 0, color: "#2D9D7A" },
            { offset: 1, color: "#48BB8E" },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  };
}

function initChart() {
  if (!chartRef.value) return;
  if (chartInstance) chartInstance.dispose();
  chartInstance = echarts.init(chartRef.value);
  chartInstance.setOption(buildOption());
}

function handleResize() { chartInstance?.resize(); }

onMounted(() => {
  initChart();
  window.addEventListener("resize", handleResize);
});

watch(() => props.data, () => {
  if (chartInstance) chartInstance.setOption(buildOption());
}, { deep: true });

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});
</script>

<style scoped>
.compare-chart { width: 100%; height: 280px; }
</style>



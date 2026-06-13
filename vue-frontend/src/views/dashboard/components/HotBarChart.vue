<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Array, default: () => [] },
});

const emit = defineEmits(["item-click"]);

const chartRef = ref(null);
let chartInstance = null;
let topData = [];

function buildOption() {
  topData = props.data.slice(0, 10).reverse();
  return {
    backgroundColor: "transparent",
    grid: { left: 80, right: 20, top: 10, bottom: 40 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(60, 40, 30, 0.9)",
      borderColor: "#D8C0B0",
      textStyle: { color: "#fff" },
      axisPointer: { type: "shadow" },
    },
    xAxis: {
      type: "value",
      axisLine: { lineStyle: { color: "#C8B0A0" } },
      axisLabel: { color: "#8B7268", fontSize: 10 },
      splitLine: { lineStyle: { color: "#E8D8CC" } },
    },
    yAxis: {
      type: "category",
      data: topData.map((d) => d.title || `ID:${d.content_id}`),
      axisLine: { lineStyle: { color: "#C8B0A0" } },
      axisLabel: { color: "#8B7268", fontSize: 10, overflow: "truncate", width: 70 },
    },
    series: [{
      type: "bar",
      data: topData.map((d) => d.hot_score),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: "#E8784A" },
          { offset: 1, color: "#F0A080" },
        ]),
        borderRadius: [0, 4, 4, 0],
      },
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
  chartInstance.on("click", (params) => {
    if (params.componentType === "series") {
      const idx = topData.length - 1 - params.dataIndex;
      const item = props.data[idx];
      if (item) emit("item-click", item);
    }
  });
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

<template>
  <div ref="chartRef" class="w-full h-64"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Array, default: () => [] },
});

const chartRef = ref(null);
let chartInstance = null;

function initChart() {
  if (!chartRef.value || !props.data.length) return;

  chartInstance = echarts.init(chartRef.value);
  
  const topData = props.data.slice(0, 10).reverse();
  
  const option = {
    backgroundColor: "transparent",
    grid: {
      left: 60,
      right: 20,
      top: 10,
      bottom: 40,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      borderColor: "#374151",
      textStyle: { color: "#fff" },
      axisPointer: { type: "shadow" },
    },
    xAxis: {
      type: "value",
      axisLine: { lineStyle: { color: "#4B5563" } },
      axisLabel: { color: "#9CA3AF", fontSize: 10 },
      splitLine: { lineStyle: { color: "#374151" } },
    },
    yAxis: {
      type: "category",
      data: topData.map((d) => `ID:${d.content_id}`),
      axisLine: { lineStyle: { color: "#4B5563" } },
      axisLabel: { color: "#9CA3AF", fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        data: topData.map((d) => d.hot_score),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#10B981" },
            { offset: 1, color: "#059669" },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
      },
    ],
  };

  chartInstance.setOption(option);
}

function handleResize() {
  chartInstance?.resize();
}

onMounted(() => {
  initChart();
  window.addEventListener("resize", handleResize);
});

watch(() => props.data, () => {
  initChart();
}, { deep: true });

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});
</script>
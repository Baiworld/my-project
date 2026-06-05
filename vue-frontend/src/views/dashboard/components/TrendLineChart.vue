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
  if (!chartRef.value) return;

  chartInstance = echarts.init(chartRef.value);
  
  const option = {
    backgroundColor: "transparent",
    grid: {
      left: 40,
      right: 20,
      top: 20,
      bottom: 40,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      borderColor: "#374151",
      textStyle: { color: "#fff" },
    },
    xAxis: {
      type: "category",
      data: props.data.map((d) => d.date),
      axisLine: { lineStyle: { color: "#4B5563" } },
      axisLabel: { color: "#9CA3AF", fontSize: 10 },
    },
    yAxis: {
      type: "value",
      axisLine: { lineStyle: { color: "#4B5563" } },
      axisLabel: { color: "#9CA3AF", fontSize: 10 },
      splitLine: { lineStyle: { color: "#374151" } },
    },
    series: [
      {
        name: "CTR",
        type: "line",
        smooth: true,
        data: props.data.map((d) => d.value),
        lineStyle: { color: "#3B82F6", width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(59, 130, 246, 0.4)" },
            { offset: 1, color: "rgba(59, 130, 246, 0)" },
          ]),
        },
        symbol: "circle",
        symbolSize: 6,
        itemStyle: { color: "#3B82F6" },
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
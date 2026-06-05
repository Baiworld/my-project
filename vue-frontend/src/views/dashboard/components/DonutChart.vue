<template>
  <div ref="chartRef" class="w-full h-48"></div>
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
  
  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      borderColor: "#374151",
      textStyle: { color: "#fff" },
      formatter: "{b}: {c}% ({d}%)",
    },
    series: [
      {
        type: "pie",
        radius: ["45%", "70%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: "#1F2937",
          borderWidth: 2,
        },
        label: {
          show: true,
          color: "#fff",
          fontSize: 12,
          formatter: "{b}\n{c}%",
        },
        labelLine: {
          lineStyle: { color: "#4B5563" },
        },
        data: [
          { value: props.data[0]?.value || 60, name: props.data[0]?.name || "音乐", itemStyle: { color: "#3B82F6" } },
          { value: props.data[1]?.value || 40, name: props.data[1]?.name || "视频", itemStyle: { color: "#F59E0B" } },
        ],
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
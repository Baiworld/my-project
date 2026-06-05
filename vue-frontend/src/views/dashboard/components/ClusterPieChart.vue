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

const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"];

function initChart() {
  if (!chartRef.value) return;

  chartInstance = echarts.init(chartRef.value);
  
  const clusterData = props.data.length 
    ? props.data.map((d, i) => ({
        value: d.user_count || 0,
        name: `簇 ${d.cluster_id}`,
        itemStyle: { color: colors[i % colors.length] },
      }))
    : [
        { value: 15, name: "簇 0", itemStyle: { color: colors[0] } },
        { value: 20, name: "簇 1", itemStyle: { color: colors[1] } },
        { value: 18, name: "簇 2", itemStyle: { color: colors[2] } },
        { value: 12, name: "簇 3", itemStyle: { color: colors[3] } },
        { value: 25, name: "簇 4", itemStyle: { color: colors[4] } },
        { value: 10, name: "簇 5", itemStyle: { color: colors[5] } },
      ];
  
  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      borderColor: "#374151",
      textStyle: { color: "#fff" },
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: "#1F2937",
          borderWidth: 2,
        },
        label: {
          show: true,
          color: "#9CA3AF",
          fontSize: 10,
          formatter: "{b}\n{c}",
        },
        labelLine: {
          lineStyle: { color: "#4B5563" },
        },
        data: clusterData,
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
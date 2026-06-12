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

const warmColors = ["#E8784A", "#F0A080", "#E8A040", "#C88030", "#D08060", "#F5C0A0"];

function initChart() {
  if (!chartRef.value || !props.data.length) return;
  if (chartInstance) chartInstance.dispose();
  chartInstance = echarts.init(chartRef.value);

  const total = props.data.reduce((s, d) => s + (d.value || 0), 0) || 1;

  const slices = props.data.map((d, i) => ({
    value: d.value || 0,
    name: d.name || `项目${i + 1}`,
    itemStyle: { color: warmColors[i % warmColors.length] },
  }));

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(60, 40, 30, 0.9)",
      borderColor: "#D8C0B0",
      textStyle: { color: "#fff" },
      formatter: (p) => {
        const pct = total > 0 ? ((p.value / total) * 100).toFixed(1) : 0;
        return `${p.name}<br/>数量: ${p.value.toLocaleString()}<br/>占比: ${pct}%`;
      },
    },
    series: [{
      type: "pie",
      radius: ["45%", "70%"],
      center: ["50%", "50%"],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: "#E8D8CC",
        borderWidth: 2,
      },
      label: {
        show: true,
        color: "#5D4037",
        fontSize: 11,
        formatter: "{b}",
      },
      labelLine: {
        lineStyle: { color: "#B8A098" },
      },
      data: slices,
    }],
  };

  chartInstance.setOption(option);
}

function handleResize() { chartInstance?.resize(); }

onMounted(() => {
  initChart();
  window.addEventListener("resize", handleResize);
});

watch(() => props.data, () => { initChart(); }, { deep: true });

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});
</script>

<style scoped>
.chart-box-sm { width: 100%; height: 200px; }
</style>

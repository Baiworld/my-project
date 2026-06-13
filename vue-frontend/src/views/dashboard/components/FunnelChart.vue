<template>
  <div ref="chartRef" class="chart-box-sm"></div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Array, default: () => [] },
});

const chartRef = ref(null);
let chartInstance = null;

const defaultData = [
  { value: 100, name: "推荐曝光", itemStyle: { color: "#E8784A" } },
  { value: 85, name: "用户点击", itemStyle: { color: "#F0A080" } },
  { value: 65, name: "完播转化", itemStyle: { color: "#F5C0A0" } },
  { value: 45, name: "冷启活跃", itemStyle: { color: "#E8A040" } },
];

function buildOption() {
  const funnelData = props.data.length > 0 ? props.data : defaultData;
  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(60, 40, 30, 0.9)",
      borderColor: "#D8C0B0",
      textStyle: { color: "#fff" },
      formatter: "{b}: {c}%",
    },
    series: [{
      type: "funnel",
      left: "10%", top: "10%", bottom: "10%", width: "80%",
      min: 0, max: 100, minSize: "0%", maxSize: "100%",
      sort: "descending", gap: 2,
      label: { show: true, position: "inside", color: "#fff", fontSize: 11, formatter: "{b}\n{c}%" },
      labelLine: { length: 10, lineStyle: { width: 1, type: "solid" } },
      itemStyle: { borderColor: "#E8D8CC", borderWidth: 1 },
      emphasis: { label: { fontSize: 12 } },
      data: funnelData,
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

watch(() => props.data, () => { updateChart(); }, { deep: true });

function handleResize() { chartInstance?.resize(); }

onMounted(() => {
  initChart();
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});
</script>

<style scoped>
.chart-box-sm { width: 100%; height: 200px; }
</style>

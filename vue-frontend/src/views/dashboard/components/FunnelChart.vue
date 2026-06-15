<template>
  <div ref="chartRef" class="chart-box-sm">
    <div v-if="isEmpty" class="empty-state">暂无转化数据</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Array, default: () => [] },
});

const chartRef = ref(null);
let chartInstance = null;

const isEmpty = computed(() => !props.data || props.data.length === 0);

function buildOption() {
  if (isEmpty.value) {
    return {
      backgroundColor: "transparent",
      title: { text: "暂无数据", left: "center", top: "center", textStyle: { color: "#8B7268", fontSize: 14 } },
    };
  }
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
      data: props.data,
    }],
  };
}

function updateChart() {
  if (!chartInstance || !chartRef.value) return;
  chartInstance.setOption(buildOption(), true);
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
.chart-box-sm {
  width: 100%;
  height: 200px;
  position: relative;
}
.empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary, #8B7268);
  font-size: var(--font-size-sm, 13px);
}
</style>

<template>
  <div ref="chartRef" class="w-full h-48"></div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: {
    type: Array,
    default: () => [],
  },
});

const chartRef = ref(null);
let chartInstance = null;

const defaultData = [
  { value: 100, name: "新用户注册", itemStyle: { color: "#3B82F6" } },
  { value: 85, name: "进入推荐页", itemStyle: { color: "#60A5FA" } },
  { value: 65, name: "点击推荐", itemStyle: { color: "#93C5FD" } },
  { value: 45, name: "完成播放", itemStyle: { color: "#10B981" } },
  { value: 30, name: "转为活跃", itemStyle: { color: "#34D399" } },
];

function initChart() {
  if (!chartRef.value) return;
  chartInstance = echarts.init(chartRef.value);
  renderChart();
}

function renderChart() {
  if (!chartInstance) return;

  const funnelData = props.data.length > 0 ? props.data : defaultData;

  chartInstance.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      borderColor: "#374151",
      textStyle: { color: "#fff" },
      formatter: "{b}: {c}%",
    },
    series: [
      {
        type: "funnel",
        left: "10%",
        top: "10%",
        bottom: "10%",
        width: "80%",
        min: 0,
        max: 100,
        minSize: "0%",
        maxSize: "100%",
        sort: "descending",
        gap: 2,
        label: {
          show: true,
          position: "inside",
          color: "#fff",
          fontSize: 11,
          formatter: "{b}\n{c}%",
        },
        labelLine: {
          length: 10,
          lineStyle: { width: 1, type: "solid" },
        },
        itemStyle: {
          borderColor: "#1F2937",
          borderWidth: 1,
        },
        emphasis: {
          label: { fontSize: 12 },
        },
        data: funnelData,
      },
    ],
  });
}

watch(() => props.data, () => renderChart(), { deep: true });

function handleResize() {
  chartInstance?.resize();
}

onMounted(() => {
  initChart();
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});
</script>

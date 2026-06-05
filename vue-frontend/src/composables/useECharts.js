import { ref, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";

const CHART_THEME = {
  // Custom ECharts theme — dark background with brand colors
};

export function useECharts(chartRef) {
  const chartInstance = ref(null);

  function initChart() {
    if (chartRef.value) {
      chartInstance.value = echarts.init(chartRef.value, CHART_THEME);
    }
  }

  function setOption(option) {
    chartInstance.value?.setOption(option, true);
  }

  function resize() {
    chartInstance.value?.resize();
  }

  onMounted(() => initChart());
  onUnmounted(() => chartInstance.value?.dispose());

  // Auto-resize on window resize
  const resizeObserver = new ResizeObserver(() => resize());
  onMounted(() => {
    if (chartRef.value) resizeObserver.observe(chartRef.value);
  });
  onUnmounted(() => resizeObserver.disconnect());

  return { chartInstance, setOption, resize };
}

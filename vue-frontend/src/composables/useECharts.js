import { ref, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";

const CHART_THEME = {};

export function useECharts(chartRef) {
  const chartInstance = ref(null);
  let resizeObserver = null;

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

  onMounted(() => {
    initChart();
    if (chartRef.value) {
      resizeObserver = new ResizeObserver(() => resize());
      resizeObserver.observe(chartRef.value);
    }
  });

  onUnmounted(() => {
    resizeObserver?.disconnect();
    chartInstance.value?.dispose();
  });

  return { chartInstance, setOption, resize };
}

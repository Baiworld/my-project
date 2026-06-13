<template>
  <div ref="chartRef" class="heatmap-container">
    <div v-if="loading" class="loading-overlay">加载地图数据...</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
});

const chartRef = ref(null);
let chartInstance = null;
let chinaGeoJSON = null;

function buildOptions() {
  const scatterData = (props.data || []).map((d) => ({
    name: d.name || "",
    value: [d.lng ?? 0, d.lat ?? 0, d.diversity ?? 50],
  }));

  const usedData = scatterData.length > 0 ? scatterData : [];

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(60,40,30,0.92)",
      borderColor: "rgba(232,120,74,0.3)",
      textStyle: { color: "#E2E8F0", fontSize: 12 },
      formatter: (p) => {
        if (p.seriesType === "scatter" || p.seriesType === "effectScatter") {
          const val = Array.isArray(p.value) ? p.value[2] : p.value;
          const level =
            val >= 80 ? "高多样性"
            : val >= 60 ? "中高多样性"
            : val >= 40 ? "中等多样性"
            : "低多样性";
          const item = props.data?.find(
            (d) => d.name === p.name
          );
          const extra = item?.cluster_size
            ? `<br/>关联用户: ${item.cluster_size}`
            : "";
          return `<b>${p.name || ""}</b><br/>特征多样性: <b style="color:#E8784A">${val}</b> (${level})${extra}`;
        }
        return p.name;
      },
    },
    visualMap: {
      min: 20,
      max: 100,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 8,
      itemWidth: 14,
      itemHeight: 120,
      textStyle: { color: "#8B7268", fontSize: 11 },
      inRange: {
        color: ["#FFE0D0", "#FFC8A0", "#F0A080", "#E8784A", "#D0653A", "#C05030"],
      },
      text: ["高多样性", "低多样性"],
      padding: [0, 0, 0, 60],
    },
    geo: {
      map: "china",
      roam: true,
      zoom: 1.15,
      center: [104.5, 36],
      itemStyle: {
        areaColor: "#FFF0E8",
        borderColor: "rgba(232,120,74,0.25)",
        borderWidth: 1,
        shadowColor: "rgba(232,120,74,0.15)",
        shadowBlur: 8,
      },
      emphasis: {
        itemStyle: {
          areaColor: "#1E1B4B",
          borderColor: "#E8784A",
          borderWidth: 2,
        },
      },
      label: {
        show: true,
        color: "rgba(148, 163, 184, 0.45)",
        fontSize: 9,
        position: "top",
      },
    },
    series: [
      {
        name: "特征多样性分布",
        type: "scatter",
        coordinateSystem: "geo",
        data: usedData,
        symbolSize: (val) => Math.max(4, (val[2] / 100) * 14),
        itemStyle: {
          color: (p) => {
            const v = p.value ? p.value[2] : 50;
            if (v >= 80) return "rgba(239, 68, 68, 0.7)";
            if (v >= 60) return "rgba(232,120,74,0.6)";
            if (v >= 40) return "rgba(232,120,74,0.55)";
            return "rgba(232,120,74,0.4)";
          },
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 0.5,
        },
        emphasis: {
          scale: 2.5,
          itemStyle: {
            shadowBlur: 12,
            shadowColor: "rgba(232,120,74,0.5)",
          },
        },
        zlevel: 1,
      },
    ],
  };
}

async function initChart() {
  if (!chartRef.value) return;

  if (!chinaGeoJSON) {
    try {
      const resp = await fetch("/china.json");
      chinaGeoJSON = await resp.json();
      echarts.registerMap("china", chinaGeoJSON);
    } catch (e) {
      console.error("Failed to load china map:", e);
      return;
    }
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }

  chartInstance.setOption(buildOptions(), true);
}

function handleResize() {
  chartInstance?.resize();
}

onMounted(() => initChart());

watch(
  () => props.data,
  () => {
    if (chartInstance && chinaGeoJSON) {
      chartInstance.setOption(buildOptions(), true);
    }
  },
  { deep: true }
);

let ro = null;
onMounted(() => {
  window.addEventListener("resize", handleResize);
  if (chartRef.value) {
    ro = new ResizeObserver(() => chartInstance?.resize());
    ro.observe(chartRef.value);
  }
});
onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
  if (ro) ro.disconnect();
});
</script>

<style scoped>
.heatmap-container {
  width: 100%;
  height: 100%;
  min-height: 520px;
  position: relative;
}
.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  z-index: 1;
}
</style>

<template>
  <div ref="chartRef" class="heatmap-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

const props = defineProps({ data: { type: Array, default: () => [] } });

const chartRef = ref(null);
let chartInstance = null;
let chinaGeoJSON = null;

const cities = [
  { name: "北京", value: [116.46, 39.92, 92] },
  { name: "上海", value: [121.48, 31.22, 88] },
  { name: "广州", value: [113.23, 23.16, 85] },
  { name: "深圳", value: [114.07, 22.62, 90] },
  { name: "成都", value: [104.06, 30.67, 78] },
  { name: "重庆", value: [106.54, 29.59, 75] },
  { name: "杭州", value: [120.19, 30.26, 86] },
  { name: "武汉", value: [114.31, 30.52, 72] },
  { name: "西安", value: [108.95, 34.27, 68] },
  { name: "南京", value: [118.78, 32.04, 80] },
  { name: "天津", value: [117.20, 39.13, 76] },
  { name: "苏州", value: [120.62, 31.32, 82] },
  { name: "长沙", value: [112.97, 28.23, 74] },
  { name: "郑州", value: [113.65, 34.76, 70] },
  { name: "青岛", value: [120.33, 36.07, 71] },
  { name: "大连", value: [121.62, 38.92, 65] },
  { name: "厦门", value: [118.08, 24.49, 83] },
  { name: "福州", value: [119.30, 26.08, 77] },
  { name: "合肥", value: [117.27, 31.86, 69] },
  { name: "沈阳", value: [123.38, 41.80, 60] },
  { name: "哈尔滨", value: [126.53, 45.80, 55] },
  { name: "昆明", value: [102.73, 25.04, 79] },
  { name: "贵阳", value: [106.71, 26.57, 73] },
  { name: "南宁", value: [108.33, 22.84, 81] },
  { name: "海口", value: [110.33, 20.03, 87] },
  { name: "兰州", value: [103.73, 36.03, 58] },
  { name: "乌鲁木齐", value: [87.68, 43.77, 45] },
  { name: "拉萨", value: [91.11, 29.97, 52] },
  { name: "呼和浩特", value: [111.65, 40.82, 56] },
  { name: "太原", value: [112.53, 37.87, 64] },
  { name: "石家庄", value: [114.48, 38.03, 67] },
  { name: "济南", value: [117.00, 36.65, 73] },
  { name: "南昌", value: [115.89, 28.68, 76] },
  { name: "长春", value: [125.35, 43.88, 58] },
  { name: "西宁", value: [101.74, 36.56, 48] },
  { name: "银川", value: [106.27, 38.47, 50] },
];

function generateHeatPoints(geoJSON) {
  const points = [];
  if (!geoJSON || !geoJSON.features) return points;
  for (const feature of geoJSON.features) {
    const name = feature.properties.name;
    const coords = feature.geometry.coordinates;
    const flat = flattenCoords(coords);
    if (flat.length < 3) continue;
    const cx = flat.reduce((s, p) => s + p[0], 0) / flat.length;
    const cy = flat.reduce((s, p) => s + p[1], 0) / flat.length;
    const hash = name.split("").reduce((s, c) => s + c.charCodeAt(0), 0);
    const diversity = 30 + (hash % 70);
    const sampleCount = Math.floor(flat.length / 200);
    for (let i = 0; i < Math.min(sampleCount, 80); i++) {
      const idx = Math.floor(Math.random() * flat.length);
      const jitter = 0.3 * (Math.random() - 0.5);
      points.push({
        name,
        value: [flat[idx][0] + jitter, flat[idx][1] + jitter, diversity],
      });
    }
  }
  return points;
}

function flattenCoords(coords) {
  if (!coords) return [];
  if (typeof coords[0] === "number") return [coords];
  return coords.flatMap((c) => flattenCoords(c));
}

function buildScatterData(geoJSON) {
  if (props.data && props.data.length > 0) {
    return props.data.map((d) => ({
      name: d.name || d.region || "",
      value: [d.lng ?? d.longitude ?? 0, d.lat ?? d.latitude ?? 0, d.diversity ?? d.value ?? 50],
    }));
  }
  return generateHeatPoints(geoJSON);
}

function buildOptions(geoJSON) {
  const heatPoints = buildScatterData(geoJSON);

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(60,40,30,0.92)",
      borderColor: "rgba(232,120,74,0.3)",
      textStyle: { color: "#E2E8F0", fontSize: 12 },
      formatter: (p) => {
        if (p.seriesType === "heatmap" || p.seriesType === "scatter") {
          const val = Array.isArray(p.value) ? p.value[2] : p.value;
          const level = val >= 80 ? "高多样性 · 冷启动效果优秀" : val >= 60 ? "中高多样性 · 效果良好" : val >= 40 ? "中等多样性 · 效果一般" : "特征单一 · 需要探索";
          return `<b>${p.name || ""}</b><br/>特征多样性: <b style="color:#E8784A">${val}</b><br/>${level}`;
        }
        return p.name;
      },
    },
    visualMap: {
      min: 30,
      max: 100,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 8,
      itemWidth: 14,
      itemHeight: 120,
      textStyle: { color: "#8B7268", fontSize: 11 },
      inRange: { color: ["#FFE0D0", "#FFC8A0", "#F0A080", "#E8784A", "#D0653A", "#C05030"] },
      text: ["高多样性(红)", "低多样性(蓝)"],
      padding: [0, 0, 0, 60],
    },
    geo: {
      map: "china",
      roam: false,
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
        name: "特征多样性",
        type: "scatter",
        coordinateSystem: "geo",
        data: heatPoints,
        symbolSize: (val) => Math.max(3, (val[2] / 100) * 8),
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
          itemStyle: { shadowBlur: 12, shadowColor: "rgba(232,120,74,0.5)" },
        },
        zlevel: 1,
      },
      {
        name: "音乐偏好城市",
        type: "effectScatter",
        coordinateSystem: "geo",
        data: cities.filter((_, i) => i % 2 === 0).map((c) => ({
          name: c.name,
          value: [c.value[0] + 0.15, c.value[1] + 0.15, c.value[2]],
        })),
        symbolSize: (val) => Math.max(5, (val[2] / 100) * 10),
        showEffectOn: "render",
        rippleEffect: {
          brushType: "stroke",
          scale: 3,
          period: 6,
          color: "rgba(240,160,128,0.3)",
        },
        itemStyle: { color: "#F0A080" },
        label: {
          show: true,
          formatter: "{b}",
          position: "right",
          color: "#8B7268",
          fontSize: 9,
          distance: 4,
        },
        zlevel: 2,
      },
      {
        name: "视频偏好城市",
        type: "effectScatter",
        coordinateSystem: "geo",
        data: cities.filter((_, i) => i % 2 === 1).map((c) => ({
          name: c.name,
          value: [c.value[0] - 0.15, c.value[1] - 0.15, c.value[2]],
        })),
        symbolSize: (val) => Math.max(5, (val[2] / 100) * 10),
        showEffectOn: "render",
        rippleEffect: {
          brushType: "stroke",
          scale: 3,
          period: 7,
          color: "rgba(240,160,128,0.3)",
        },
        itemStyle: { color: "#E8A040" },
        label: { show: false },
        zlevel: 2,
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

  chartInstance.setOption(buildOptions(chinaGeoJSON), true);
}

function handleResize() {
  chartInstance?.resize();
}

onMounted(() => initChart());
watch(() => props.data, () => { if (chartInstance && chinaGeoJSON) chartInstance.setOption(buildOptions(chinaGeoJSON), true); }, { deep: true });
onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});

let ro = null;
onMounted(() => {
  window.addEventListener("resize", handleResize);
  if (chartRef.value) {
    ro = new ResizeObserver(() => chartInstance?.resize());
    ro.observe(chartRef.value);
  }
});
onUnmounted(() => {
  if (ro) ro.disconnect();
});
</script>

<style scoped>
.heatmap-container {
  width: 100%;
  height: 100%;
  min-height: 520px;
}
</style>

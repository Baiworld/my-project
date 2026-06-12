<template>
  <div class="profile-detail">
    <div v-if="loading" class="loading">加载中...</div>
    <template v-else-if="profile">
      <h4>实时画像</h4>
      <div class="profile-fields">
        <p><strong>用户ID：</strong>{{ profile.user_id }}</p>
        <p><strong>行为次数：</strong>{{ rt?.behavior_count ?? "-" }}</p>
        <p><strong>播放次数：</strong>{{ rt?.play_count ?? "-" }}</p>
        <p><strong>点赞率：</strong>{{ formatPct(rt?.like_rate) }}</p>
        <p><strong>收藏率：</strong>{{ formatPct(rt?.favorite_rate) }}</p>
        <p><strong>跳过率：</strong>{{ formatPct(rt?.skip_rate) }}</p>
        <p><strong>冷启动：</strong>{{ rt?.is_cold_start ? "是" : "否" }}</p>
        <p><strong>内容偏好：</strong>{{ rt?.content_type_ratio }}</p>
      </div>
      <h4>离线画像</h4>
      <div class="profile-fields">
        <p><strong>生命周期：</strong>{{ off?.lifecycle_stage ?? "-" }}</p>
        <p><strong>总行为数：</strong>{{ off?.total_behaviors ?? "-" }}</p>
        <p><strong>平均会话时长：</strong>{{ off?.avg_session_duration ?? "-" }}s</p>
        <p><strong>近30天活跃天数：</strong>{{ off?.active_days_last_30 ?? "-" }}</p>
        <p><strong>偏好标签：</strong>{{ formatTags(off?.long_term_tags) }}</p>
        <p><strong>偏好内容类型：</strong>{{ off?.favorite_content_type ?? "-" }}</p>
        <p><strong>聚类ID：</strong>{{ off?.cluster_id ?? "-" }}</p>
        <p><strong>最后活跃：</strong>{{ off?.last_active_time ?? "-" }}</p>
      </div>
    </template>
    <div v-else class="empty">暂无数据</div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import api from "@/api";

const props = defineProps({ userId: { type: [Number, String], default: null } });

const profile = ref(null);
const loading = ref(false);

const rt = computed(() => profile.value?.real_time ?? null);
const off = computed(() => profile.value?.offline ?? null);

function formatPct(v) {
  if (v == null) return "-";
  return (Number(v) * 100).toFixed(1) + "%";
}
function formatTags(tags) {
  if (!tags) return "-";
  try {
    const arr = typeof tags === "string" ? JSON.parse(tags) : tags;
    return Array.isArray(arr) ? arr.slice(0, 10).join("、") : "-";
  } catch { return "-"; }
}

async function load(userId) {
  if (!userId) return;
  loading.value = true;
  try {
    const resp = await api.users.getProfile(userId);
    if (resp.data?.code === 200) {
      profile.value = resp.data.data;
    }
  } catch (e) {
    console.error("Failed to load profile:", e);
  } finally {
    loading.value = false;
  }
}

watch(() => props.userId, (v) => load(v), { immediate: true });
</script>

<style scoped>
.profile-detail { padding: 12px 0; }
.profile-detail h4 { color: #C7D2FE; margin: 16px 0 8px; font-size: 14px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 4px; }
.profile-fields p { margin: 4px 0; font-size: 13px; color: #B0B5CC; }
.profile-fields strong { color: #94A3B8; }
.loading, .empty { color: #8B90A8; font-size: 13px; padding: 20px 0; text-align: center; }
</style>

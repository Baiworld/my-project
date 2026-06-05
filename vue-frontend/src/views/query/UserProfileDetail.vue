<template>
  <div class="profile-detail">
    <h4>用户画像详情</h4>
    <div class="profile-fields">
      <p><strong>用户ID：</strong>{{ profile.user_id }}</p>
      <p><strong>行为数：</strong>{{ profile.behavior_count }}</p>
      <p><strong>生命周期：</strong>{{ profile.lifecycle }}</p>
      <p><strong>偏好标签：</strong>{{ profile.tags?.join(", ") }}</p>
      <p><strong>冷启动群组：</strong>{{ profile.cluster_id }}</p>
    </div>
    <h4>推荐列表</h4>
    <ul>
      <li v-for="item in profile.recommendations" :key="item.content_id">
        {{ item.title }} — {{ item.score?.toFixed(4) }}
      </li>
    </ul>
  </div>
</template>

<script setup>
defineProps({ profile: Object });
</script>

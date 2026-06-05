<template>
  <div class="paginator">
    <button :disabled="currentPage <= 1" @click="$emit('change', currentPage - 1)">上一页</button>
    <span>{{ currentPage }} / {{ totalPages }}</span>
    <button :disabled="currentPage >= totalPages" @click="$emit('change', currentPage + 1)">下一页</button>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  total: { type: Number, default: 0 },
  pageSize: { type: Number, default: 20 },
  currentPage: { type: Number, default: 1 },
});

defineEmits(["change"]);

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));
</script>

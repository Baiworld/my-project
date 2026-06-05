<template>
  <div class="date-picker">
    <input type="date" :value="modelValue.start" @input="updateStart" />
    <span>至</span>
    <input type="date" :value="modelValue.end" @input="updateEnd" />
  </div>
</template>

<script setup>
const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

function updateStart(e) {
  emit("update:modelValue", { ...props.modelValue, start: e.target.value });
}
function updateEnd(e) {
  emit("update:modelValue", { ...props.modelValue, end: e.target.value });
}
</script>

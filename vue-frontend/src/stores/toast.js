import { defineStore } from "pinia";
import { ref } from "vue";

let _id = 0;

export const useToastStore = defineStore("toast", () => {
  const toasts = ref([]);

  function add(message, type = "info", duration = 3500) {
    const id = ++_id;
    toasts.value.push({ id, message, type, duration, leaving: false });
    if (duration > 0) {
      setTimeout(() => remove(id), duration);
    }
    return id;
  }

  function remove(id) {
    const t = toasts.value.find((x) => x.id === id);
    if (!t) return;
    t.leaving = true;
    setTimeout(() => {
      toasts.value = toasts.value.filter((x) => x.id !== id);
    }, 260);
  }

  function success(msg, dur) { return add(msg, "success", dur); }
  function error(msg, dur) { return add(msg, "error", dur ?? 5000); }
  function warning(msg, dur) { return add(msg, "warning", dur); }
  function info(msg, dur) { return add(msg, "info", dur); }

  return { toasts, add, remove, success, error, warning, info };
});

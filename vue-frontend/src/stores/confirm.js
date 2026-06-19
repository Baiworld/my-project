import { defineStore } from "pinia";
import { ref } from "vue";

export const useConfirmStore = defineStore("confirm", () => {
  const visible = ref(false);
  const title = ref("");
  const message = ref("");
  const confirmText = ref("确认");
  const cancelText = ref("取消");
  const variant = ref("danger"); // danger | warning | info
  let _resolve = null;

  function open(opts = {}) {
    title.value = opts.title || "确认操作";
    message.value = opts.message || "确定要执行此操作吗？";
    confirmText.value = opts.confirmText || "确认";
    cancelText.value = opts.cancelText || "取消";
    variant.value = opts.variant || "danger";
    visible.value = true;
    return new Promise((resolve) => {
      _resolve = resolve;
    });
  }

  function confirm() {
    visible.value = false;
    if (_resolve) _resolve(true);
    _resolve = null;
  }

  function cancel() {
    visible.value = false;
    if (_resolve) _resolve(false);
    _resolve = null;
  }

  return { visible, title, message, confirmText, cancelText, variant, open, confirm, cancel };
});

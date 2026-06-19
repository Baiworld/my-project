import { defineStore } from "pinia";
import { ref, watch } from "vue";

const KEY = "app-theme";

function getSaved() {
  try { return localStorage.getItem(KEY) || "light"; } catch { return "light"; }
}

export const useThemeStore = defineStore("theme", () => {
  const mode = ref(getSaved());

  function apply() {
    document.documentElement.setAttribute("data-theme", mode.value);
    try { localStorage.setItem(KEY, mode.value); } catch {}
  }

  function toggle() {
    mode.value = mode.value === "dark" ? "light" : "dark";
    apply();
  }

  function set(m) {
    mode.value = m;
    apply();
  }

  apply();

  return { mode, toggle, set };
});

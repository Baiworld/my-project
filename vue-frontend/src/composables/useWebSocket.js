import { ref, onUnmounted } from "vue";
import { io } from "socket.io-client";

const SERVER_URL = "http://localhost:5000";
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const HEARTBEAT_INTERVAL_MS = 25000;

export function useWebSocket() {
  const connected = ref(false);
  let socket = null;
  let heartbeatTimer = null;
  let reconnectAttempts = 0;

  function connect() {
    socket = io(SERVER_URL, {
      reconnection: false, // manual exponential backoff
    });

    socket.on("connect", () => {
      connected.value = true;
      reconnectAttempts = 0;
      startHeartbeat();
    });

    socket.on("disconnect", () => {
      connected.value = false;
      stopHeartbeat();
      scheduleReconnect();
    });
  }

  function scheduleReconnect() {
    const delay = Math.min(
      RECONNECT_BASE_MS * Math.pow(2, reconnectAttempts),
      RECONNECT_MAX_MS
    );
    reconnectAttempts++;
    setTimeout(connect, delay);
  }

  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      socket.emit("ping");
    }, HEARTBEAT_INTERVAL_MS);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  function on(event, callback) {
    if (socket) socket.on(event, callback);
  }

  function off(event, callback) {
    if (socket) socket.off(event, callback);
  }

  onUnmounted(() => {
    stopHeartbeat();
    if (socket) socket.disconnect();
  });

  return { connected, connect, on, off };
}

<template>
  <div class="admin-page">
    <!-- Header -->
    <header class="page-header">
      <div class="header-left">
        <button @click="goBack" class="back-btn" title="返回首页">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4l-6 6 6 6"/></svg>
        </button>
        <div>
          <h1>系统管理</h1>
          <p>用户管理与系统设置</p>
        </div>
      </div>
    </header>

    <div class="admin-content">
      <!-- Tabs -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="['tab-btn', { active: activeTab === tab.id }]"
        >
          {{ tab.name }}
        </button>
      </div>

      <!-- ═══ User Management ═══ -->
      <div v-if="activeTab === 'users'" class="user-panel anim-fade-in-up">
        <div class="panel-toolbar">
          <h3>用户列表</h3>
          <button @click="openAddModal" class="btn btn-success btn-sm">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M8 3v10M3 8h10"/></svg>
            添加用户
          </button>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width:60px">ID</th>
                <th>用户名</th>
                <th>邮箱</th>
                <th style="width:100px">角色</th>
                <th style="width:80px">状态</th>
                <th style="width:160px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id">
                <td class="id-cell">{{ user.id }}</td>
                <td>
                  <div class="user-cell">
                    <div class="user-avatar">{{ user.username?.charAt(0)?.toUpperCase() }}</div>
                    <span>{{ user.username }}</span>
                  </div>
                </td>
                <td class="email-cell">{{ user.email }}</td>
                <td>
                  <span :class="['badge', getRoleBadge(user.role)]">{{ getRoleLabel(user.role) }}</span>
                </td>
                <td>
                  <span :class="['status-dot', user.status === 'active' ? 'on' : 'off']"></span>
                  {{ user.status === 'active' ? '活跃' : '禁用' }}
                </td>
                <td>
                  <div class="action-btns">
                    <button @click="editUser(user)" class="action-btn" title="编辑">
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M11 2l3 3-9 9H2v-3l9-9z"/></svg>
                    </button>
                    <button @click="toggleUserStatus(user)" class="action-btn" :title="user.status === 'active' ? '禁用' : '启用'">
                      <svg v-if="user.status === 'active'" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><path d="M5 5l6 6M11 5l-6 6"/></svg>
                      <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 8h10"/><circle cx="8" cy="8" r="6"/></svg>
                    </button>
                    <button @click="deleteUser(user.id)" class="action-btn danger" title="删除">
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 5h10M6 5V3a1 1 0 011-1h2a1 1 0 011 1v2M13 5v8a1 1 0 01-1 1H4a1 1 0 01-1-1V5"/></svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ═══ System Settings ═══ -->
      <div v-if="activeTab === 'settings'" class="settings-panel anim-fade-in-up">
        <div class="surface-card" style="padding:28px">
          <h3 style="font-size:16px;font-weight:600;margin-bottom:24px">系统参数配置</h3>
          <div class="settings-grid">
            <div class="field">
              <label>推荐刷新周期（小时）</label>
              <input v-model.number="settings.refreshInterval" type="number" min="1" class="input-field" aria-label="推荐刷新周期" />
            </div>
            <div class="field">
              <label>推荐数量</label>
              <input v-model.number="settings.recommendCount" type="number" min="1" class="input-field" aria-label="推荐数量" />
            </div>
            <div class="field">
              <label>冷启动聚类数量</label>
              <input v-model.number="settings.clusterCount" type="number" min="2" class="input-field" aria-label="冷启动聚类数量" />
            </div>
            <div class="field">
              <label>音乐 / 视频比例</label>
              <div class="ratio-input">
                <input v-model.number="settings.musicRatio" type="range" min="0" max="100" class="range-slider" aria-label="音乐视频比例" />
                <span class="ratio-value">{{ settings.musicRatio }} : {{ 100 - settings.musicRatio }}</span>
              </div>
            </div>
          </div>
          <button @click="saveSettings" class="btn btn-primary" style="margin-top:20px">保存设置</button>
        </div>
      </div>

      <!-- ═══ Audit Logs ═══ -->
      <div v-if="activeTab === 'audit'" class="audit-panel anim-fade-in-up">
        <div class="surface-card" style="padding:24px">
          <h3 style="font-size:16px;font-weight:600;margin-bottom:16px">操作审计记录</h3>
          <div class="audit-filters">
            <div class="field" style="flex:1">
              <label>操作类型</label>
              <select v-model="auditFilter.action" @change="loadAuditLogs(1)" class="select-field" aria-label="操作类型">
                <option value="">全部</option>
                <option value="create_user">创建用户</option>
                <option value="update_user">编辑用户</option>
                <option value="delete_user">删除用户</option>
                <option value="toggle_user">切换状态</option>
                <option value="update_settings">修改设置</option>
                <option value="query">数据查询</option>
              </select>
            </div>
            <button @click="loadAuditLogs(1)" class="btn btn-primary btn-sm" style="align-self:flex-end">查询</button>
          </div>
          <div class="table-wrap" style="margin-top:12px">
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width:60px">ID</th>
                  <th style="width:80px">操作人</th>
                  <th style="width:120px">操作类型</th>
                  <th>操作对象</th>
                  <th style="width:160px">时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in auditLogs" :key="log.id">
                  <td class="id-cell">{{ log.id }}</td>
                  <td>{{ log.operator_id }}</td>
                  <td><span :class="['badge', auditActionBadge(log.action)]">{{ auditActionLabel(log.action) }}</span></td>
                  <td class="email-cell">{{ log.target }}</td>
                  <td style="font-size:12px;color:var(--text-tertiary)">{{ log.created_at?.replace('T', ' ').substring(0, 19) }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="auditLogs.length === 0 && !auditLoading" class="empty-state" style="padding:32px">
              <p class="empty-title">暂无审计记录</p>
              <span class="empty-hint">系统操作记录将显示在这里</span>
            </div>
            <div v-if="auditLoading" class="empty-state" style="padding:32px"><p>加载中...</p></div>
          </div>
          <div v-if="auditPagination.total > 0" class="table-pagination" style="margin-top:12px">
            <span class="page-info">第 {{ auditPagination.page }} / {{ auditPagination.totalPages }} 页，共 {{ auditPagination.total }} 条</span>
            <div class="page-btns">
              <button @click="loadAuditLogs(auditPagination.page - 1)" :disabled="auditPagination.page <= 1" class="btn btn-ghost btn-sm">← 上一页</button>
              <button @click="loadAuditLogs(auditPagination.page + 1)" :disabled="auditPagination.page >= auditPagination.totalPages" class="btn btn-ghost btn-sm">下一页 →</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Modal ═══ -->
    <teleport to="body">
      <transition name="modal">
        <div v-if="showAddModal" class="modal-overlay" @click.self="closeModal">
          <div class="modal-card anim-fade-in-scale">
            <div class="modal-header">
              <h3>{{ editingUser ? '编辑用户' : '添加用户' }}</h3>
              <button @click="closeModal" class="modal-close">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 5l10 10M15 5L5 15"/></svg>
              </button>
            </div>

            <div class="modal-body">
              <div class="field">
                <label>用户名</label>
                <input v-model="userForm.username" type="text" class="input-field" placeholder="请输入用户名" required />
              </div>
              <div class="field">
                <label>邮箱</label>
                <input v-model="userForm.email" type="email" class="input-field" placeholder="请输入邮箱" required />
              </div>
              <div class="field">
                <label>密码{{ editingUser ? '（留空则不修改）' : '' }}</label>
                <input v-model="userForm.password" type="password" class="input-field" placeholder="请输入密码" :required="!editingUser" />
              </div>
              <div class="field">
                <label>角色</label>
                <select v-model="userForm.role" class="select-field" aria-label="角色">
                  <option value="end_user">普通用户</option>
                  <option value="operator">操作员</option>
                  <option value="admin">管理员</option>
                </select>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeModal" class="btn btn-ghost">取消</button>
              <button @click="saveUser" class="btn btn-primary">{{ editingUser ? '更新' : '创建' }}</button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import api from "@/api";
import { useConfirmStore } from "@/stores/confirm";
import { useToastStore } from "@/stores/toast";

const router = useRouter();
const confirmStore = useConfirmStore();
const toastStore = useToastStore();

const activeTab = ref("users");
const tabs = [
  { id: "users", name: "用户管理" },
  { id: "settings", name: "系统设置" },
  { id: "audit", name: "审计日志" },
];

const users = ref([]);
const showAddModal = ref(false);
const editingUser = ref(null);
const userForm = reactive({
  username: "", email: "", password: "", role: "end_user",
});

const settings = reactive({
  refreshInterval: 6, recommendCount: 20, clusterCount: 8, musicRatio: 60,
});

function getRoleLabel(role) {
  const labels = { end_user: "普通用户", operator: "操作员", admin: "管理员" };
  return labels[role] || role;
}
function getRoleBadge(role) {
  const map = { end_user: "badge-gray", operator: "badge-blue", admin: "badge-purple" };
  return map[role] || "badge-gray";
}

async function loadUsers() {
  try {
    const response = await api.get("/api/users");
    users.value = response.data.data || response.data;
  } catch (error) {
    console.error("加载用户失败:", error);
  }
}

function openAddModal() {
  editingUser.value = null;
  userForm.username = "";
  userForm.email = "";
  userForm.password = "";
  userForm.role = "end_user";
  showAddModal.value = true;
}

function editUser(user) {
  editingUser.value = user;
  userForm.username = user.username;
  userForm.email = user.email;
  userForm.password = "";
  userForm.role = user.role;
  showAddModal.value = true;
}

function closeModal() {
  showAddModal.value = false;
  editingUser.value = null;
}

async function saveUser() {
  try {
    if (editingUser.value) {
      const payload = { username: userForm.username, email: userForm.email, role: userForm.role };
      if (userForm.password) payload.password = userForm.password;
      await api.put(`/api/users/${editingUser.value.id}`, payload);
      toastStore.success("用户更新成功");
    } else {
      await api.post("/api/users", { ...userForm });
      toastStore.success("用户创建成功");
    }
    closeModal();
    await loadUsers();
  } catch (error) {
    toastStore.error(error.response?.data?.message || "保存用户失败");
  }
}

async function toggleUserStatus(user) {
  try {
    const newStatus = user.status === "active" ? "inactive" : "active";
    const actionLabel = newStatus === "inactive" ? "禁用" : "启用";
    const ok = await confirmStore.open({
      title: `${actionLabel}用户`,
      message: `确定要${actionLabel}用户「${user.username}」吗？`,
      confirmText: actionLabel,
      variant: "warning",
    });
    if (!ok) return;
    await api.put(`/api/users/${user.id}/status`, { status: newStatus });
    user.status = newStatus;
    toastStore.success(`用户已${actionLabel}`);
  } catch (error) {
    toastStore.error("更新状态失败");
  }
}

async function deleteUser(userId) {
  const ok = await confirmStore.open({
    title: "删除用户",
    message: "确定要删除该用户吗？此操作不可撤销。",
    confirmText: "删除",
    variant: "danger",
  });
  if (!ok) return;
  try {
    await api.delete(`/api/users/${userId}`);
    users.value = users.value.filter((u) => u.id !== userId);
    toastStore.success("用户已删除");
  } catch (error) {
    toastStore.error("删除用户失败");
  }
}

async function saveSettings() {
  try {
    await api.put("/api/settings", { ...settings });
    toastStore.success("设置保存成功");
  } catch (error) {
    toastStore.error("保存设置失败");
  }
}

// ── 审计日志 ──
const auditLogs = ref([]);
const auditLoading = ref(false);
const auditFilter = reactive({ action: "" });
const auditPagination = reactive({ page: 1, size: 20, total: 0, totalPages: 0 });

function auditActionLabel(action) {
  const map = { create_user: "创建用户", update_user: "编辑用户", delete_user: "删除用户", toggle_user: "切换状态", update_settings: "修改设置", query: "数据查询" };
  return map[action] || action;
}
function auditActionBadge(action) {
  const map = { create_user: "badge-green", update_user: "badge-blue", delete_user: "badge-red", toggle_user: "badge-yellow", update_settings: "badge-purple", query: "badge-gray" };
  return map[action] || "badge-gray";
}

async function loadAuditLogs(page = 1) {
  auditLoading.value = true;
  try {
    const params = new URLSearchParams();
    params.append("page", page);
    params.append("size", auditPagination.size);
    if (auditFilter.action) params.append("action", auditFilter.action);
    const response = await api.get(`/api/audit-logs?${params}`);
    const payload = response.data;
    auditLogs.value = payload.data || [];
    if (payload.pagination) {
      auditPagination.page = payload.pagination.page;
      auditPagination.total = payload.pagination.total;
      auditPagination.totalPages = payload.pagination.pages;
    }
  } catch (error) {
    console.error("加载审计日志失败:", error);
  } finally {
    auditLoading.value = false;
  }
}

function goBack() {
  router.push("/dashboard");
}

onMounted(() => {
  loadUsers();
});

watch(activeTab, (tab) => {
  if (tab === "audit") loadAuditLogs();
});
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--bg-root);
  color: var(--text-primary);
}

/* ── Header ── */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.header-left h1 { font-size: var(--font-size-lg); font-weight: 700; }
.header-left p  { font-size: var(--font-size-xs); color: var(--text-tertiary); margin-top: 1px; }

.back-btn {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); color: var(--text-secondary); cursor: pointer;
  transition: all var(--duration-fast) ease;
}
.back-btn:hover { background: rgba(255,255,255,0.08); color: var(--text-primary); }
.back-btn svg { width: 18px; height: 18px; }

/* ── Content ── */
.admin-content { max-width: 1100px; margin: 0 auto; padding: 24px; }
.tab-bar { display: flex; gap: 6px; margin-bottom: 20px; }

/* ── Panel ── */
.panel-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.panel-toolbar h3 { font-size: var(--font-size-base); font-weight: 600; }

.table-wrap {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* ── Table customizations ── */
.id-cell { font-family: var(--font-mono); font-size: var(--font-size-xs); color: var(--text-tertiary); }
.email-cell { color: var(--text-secondary); }

.user-cell { display: flex; align-items: center; gap: 10px; }
.user-avatar {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  background: linear-gradient(135deg, #E8784A, #F0A080);
  color: #fff; font-size: 13px; font-weight: 600;
  flex-shrink: 0;
}

.status-dot {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 6px;
}
.status-dot.on  { background: #34D399; }
.status-dot.off { background: #F87171; }

.action-btns { display: flex; gap: 4px; }
.action-btn {
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid transparent;
  border-radius: 6px; color: var(--text-secondary); cursor: pointer;
  transition: all var(--duration-fast) ease;
}
.action-btn:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); border-color: var(--border-default); }
.action-btn.danger:hover { color: #F87171; background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.25); }
.action-btn svg { width: 14px; height: 14px; }

/* ── Settings ── */
.settings-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label {
  font-size: var(--font-size-xs); font-weight: 500;
  color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em;
}
.ratio-input { display: flex; align-items: center; gap: 14px; }
.range-slider {
  flex: 1; height: 4px;
  -webkit-appearance: none; appearance: none;
  background: rgba(255,255,255,0.1); border-radius: 2px; outline: none;
}
.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--color-primary); cursor: pointer;
  box-shadow: 0 2px 8px var(--color-primary-glow);
}
.ratio-value {
  font-size: var(--font-size-sm); color: var(--text-secondary);
  font-family: var(--font-mono); min-width: 70px; text-align: right;
}

/* ═══════ Modal ═══════ */
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  display: flex; align-items: center; justify-content: center;
  background: rgba(60,40,30,0.4);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}

.modal-card {
  width: 440px; max-width: 92vw;
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  box-shadow: 0 16px 48px rgba(120,80,50,0.15);
}

.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 0;
}
.modal-header h3 { font-size: var(--font-size-lg); font-weight: 700; }
.modal-close {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.04); border: none; border-radius: 8px;
  color: var(--text-secondary); cursor: pointer; transition: all var(--duration-fast) ease;
}
.modal-close:hover { background: rgba(255,255,255,0.1); color: var(--text-primary); }
.modal-close svg { width: 16px; height: 16px; }

.modal-body {
  padding: 20px 24px;
  display: flex; flex-direction: column; gap: 16px;
}

.modal-footer {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 0 24px 20px;
}

/* ── Modal transitions ── */
.modal-enter-active { transition: opacity 0.25s ease; }
.modal-enter-active .modal-card { animation: fadeInScale 0.3s cubic-bezier(0.19,1,0.22,1); }
.modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from,
.modal-leave-to { opacity: 0; }

/* ── Empty state ── */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.empty-title { font-size: var(--font-size-base); font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.empty-hint { font-size: var(--font-size-xs); color: var(--text-tertiary); }
</style>

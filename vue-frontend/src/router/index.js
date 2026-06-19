import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/login/LoginView.vue"),
    meta: { guest: true },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("@/views/login/RegisterView.vue"),
    meta: { guest: true },
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: () => import("@/views/dashboard/DashboardView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/query",
    name: "Query",
    component: () => import("@/views/query/QueryView.vue"),
    meta: { requiresAuth: true, roles: ["operator", "admin"] },
  },
  {
    path: "/query/user/:id",
    name: "UserProfileDetail",
    component: () => import("@/views/query/UserProfileDetail.vue"),
    meta: { requiresAuth: true, roles: ["operator", "admin"] },
  },
  {
    path: "/admin",
    name: "Admin",
    component: () => import("@/views/admin/AdminView.vue"),
    meta: { requiresAuth: true, roles: ["admin"] },
  },
  {
    path: "/content/:id",
    name: "ContentDetail",
    component: () => import("@/views/content/ContentDetail.vue"),
    meta: { requiresAuth: true, roles: ["operator", "admin"] },
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/dashboard",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next("/login");
    return;
  }

  if (to.meta.roles && !to.meta.roles.some((r) => authStore.hasRole(r))) {
    next("/dashboard");
    return;
  }

  if (to.meta.guest && authStore.isAuthenticated) {
    next("/dashboard");
    return;
  }

  next();
});

export default router;

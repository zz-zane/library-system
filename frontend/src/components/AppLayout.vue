<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activePath = computed(() => route.path)

const operatorName = computed(
  () => authStore.user?.display_name ?? authStore.user?.username ?? ''
)

async function handleLogout(): Promise<void> {
  authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <el-container class="app-layout">
    <el-header class="app-header" height="56px">
      <span class="app-title">图书管理员系统</span>
      <el-menu
        class="app-menu"
        mode="horizontal"
        :default-active="activePath"
        router
        :ellipsis="false"
      >
        <el-menu-item index="/books">图书管理</el-menu-item>
        <el-menu-item index="/readers">读者管理</el-menu-item>
        <el-menu-item index="/borrows">借阅管理</el-menu-item>
        <el-menu-item index="/users">操作员</el-menu-item>
      </el-menu>
      <div class="app-user">
        <span class="operator-name">{{ operatorName }}</span>
        <el-button type="primary" link @click="handleLogout">退出登录</el-button>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 32px;
  border-bottom: 1px solid var(--el-border-color);
  background: #fff;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  white-space: nowrap;
}

.app-menu {
  flex: 1;
  border-bottom: none;
}

.app-user {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.operator-name {
  color: #4b5563;
  font-size: 14px;
}

.app-main {
  background: #f7f8fa;
}
</style>

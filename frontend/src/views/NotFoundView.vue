<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 404 页无认证要求：登录状态回首页，未登录去登录页
function goBack(): void {
  if (authStore.isAuthenticated) {
    void router.replace('/books')
  } else {
    void router.replace('/login')
  }
}
</script>

<template>
  <main class="not-found-page">
    <el-result icon="warning" title="404" sub-title="页面不存在或已被移除">
      <template #extra>
        <el-button type="primary" @click="goBack">返回</el-button>
      </template>
    </el-result>
  </main>
</template>

<style scoped>
.not-found-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f7f8fa;
}
</style>

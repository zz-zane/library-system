<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppLayout from '@/components/AppLayout.vue'

const route = useRoute()

// 受保护页面挂在主布局内，登录页与 404 页全屏渲染
const useLayout = computed(() => route.meta.requiresAuth === true)
</script>

<template>
  <AppLayout v-if="useLayout" />
  <router-view v-else />
</template>

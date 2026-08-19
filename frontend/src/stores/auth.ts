import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchMeApi, loginApi } from '@/api/auth'
import {
  clearToken,
  getToken,
  registerUnauthorizedHandler,
  setToken
} from '@/api/http'
import type { LoginRequest } from '@/types/auth'
import type { UserOut } from '@/types/user'

// 认证全局状态，约定见 docs/system-design.md 11.3
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const user = ref<UserOut | null>(null)

  const isAuthenticated = computed(() => token.value !== null)

  function applyToken(value: string): void {
    token.value = value
    setToken(value)
  }

  function clearAuth(): void {
    token.value = null
    user.value = null
    clearToken()
  }

  async function login(credentials: LoginRequest): Promise<void> {
    const { data } = await loginApi(credentials)
    applyToken(data.access_token)
    await fetchMe()
  }

  async function fetchMe(): Promise<void> {
    const { data } = await fetchMeApi()
    user.value = data
  }

  function logout(): void {
    clearAuth()
  }

  // 受保护接口返回 401（token 失效、账号停用等）时统一清理本地认证状态
  registerUnauthorizedHandler(clearAuth)

  return {
    token,
    user,
    isAuthenticated,
    login,
    fetchMe,
    logout,
    clearAuth
  }
})

import axios, { AxiosError } from 'axios'

import type { ValidationErrorItem } from '@/types/common'

// 统一 axios 实例，约定见 docs/system-design.md 11.4
export const http = axios.create({
  baseURL: '/api',
  timeout: 10_000
})

const TOKEN_KEY = 'library_admin_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 清理回调由 auth store 注册，避免 http 层与 store 循环依赖
let onUnauthorized: (() => void) | null = null

export function registerUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && onUnauthorized) {
      onUnauthorized()
    }
    return Promise.reject(error)
  }
)

/** 从 axios 错误中提取用户可读提示 */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.length > 0) {
      return detail
    }
    if (Array.isArray(detail)) {
      const messages = (detail as ValidationErrorItem[])
        .map((item) => item.msg)
        .filter((msg) => typeof msg === 'string' && msg.length > 0)
      if (messages.length > 0) {
        return messages.join('；')
      }
    }
    if (error.code === 'ECONNABORTED') {
      return '请求超时，请稍后重试'
    }
    if (!error.response) {
      return '网络异常，请检查连接后重试'
    }
    return '请求失败，请稍后重试'
  }
  return '发生未知错误'
}

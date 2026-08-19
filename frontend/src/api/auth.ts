import { http } from './http'

import type { LoginRequest, TokenOut } from '@/types/auth'
import type { UserOut } from '@/types/user'

// 认证 API，契约见 docs/system-design.md 8.2
export function loginApi(payload: LoginRequest) {
  return http.post<TokenOut>('/auth/login', payload)
}

export function fetchMeApi() {
  return http.get<UserOut>('/auth/me')
}

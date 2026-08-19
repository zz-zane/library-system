import { http } from './http'

import type { Page } from '@/types/common'
import type { UserCreate, UserOut, UserQuery, UserUpdate } from '@/types/user'

// 操作员 API，契约见 docs/system-design.md 8.3
export function listUsersApi(params: UserQuery) {
  return http.get<Page<UserOut>>('/users', { params })
}

export function createUserApi(payload: UserCreate) {
  return http.post<UserOut>('/users', payload)
}

export function updateUserApi(userId: number, payload: UserUpdate) {
  return http.put<UserOut>(`/users/${userId}`, payload)
}

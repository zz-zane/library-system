import { http } from './http'

import type { BorrowCreate, BorrowOut, BorrowQuery } from '@/types/borrow'
import type { Page } from '@/types/common'

// 借阅 API，契约见 docs/system-design.md 8.6
export function listBorrowsApi(params: BorrowQuery) {
  return http.get<Page<BorrowOut>>('/borrows', { params })
}

export function createBorrowApi(payload: BorrowCreate) {
  return http.post<BorrowOut>('/borrows', payload)
}

export function returnBorrowApi(borrowId: number) {
  return http.post<BorrowOut>(`/borrows/${borrowId}/return`)
}

export function getBorrowApi(borrowId: number) {
  return http.get<BorrowOut>(`/borrows/${borrowId}`)
}

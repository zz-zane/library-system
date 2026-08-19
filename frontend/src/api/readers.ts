import { http } from './http'

import type { Page } from '@/types/common'
import type { ReaderCreate, ReaderOut, ReaderQuery, ReaderUpdate } from '@/types/reader'

// 读者 API，契约见 docs/system-design.md 8.5
export function listReadersApi(params: ReaderQuery) {
  return http.get<Page<ReaderOut>>('/readers', { params })
}

export function createReaderApi(payload: ReaderCreate) {
  return http.post<ReaderOut>('/readers', payload)
}

export function updateReaderApi(readerId: number, payload: ReaderUpdate) {
  return http.put<ReaderOut>(`/readers/${readerId}`, payload)
}

export function deleteReaderApi(readerId: number) {
  return http.delete<void>(`/readers/${readerId}`)
}

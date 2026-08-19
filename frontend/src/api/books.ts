import { http } from './http'

import type { BookCreate, BookOut, BookQuery, BookUpdate } from '@/types/book'
import type { Page } from '@/types/common'

// 图书 API，契约见 docs/system-design.md 8.4
export function listBooksApi(params: BookQuery) {
  return http.get<Page<BookOut>>('/books', { params })
}

export function createBookApi(payload: BookCreate) {
  return http.post<BookOut>('/books', payload)
}

export function updateBookApi(bookId: number, payload: BookUpdate) {
  return http.put<BookOut>(`/books/${bookId}`, payload)
}

export function deleteBookApi(bookId: number) {
  return http.delete<void>(`/books/${bookId}`)
}

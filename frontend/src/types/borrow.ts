// 借阅类型，契约见 docs/system-design.md 8.6
import type { BookBriefOut } from './book'
import type { ReaderBriefOut } from './reader'
import type { UserBriefOut } from './user'

export type BorrowStatus = 'borrowed' | 'overdue' | 'returned'

export interface BorrowOut {
  id: number
  book: BookBriefOut
  reader: ReaderBriefOut
  borrowed_by: UserBriefOut
  borrowed_at: string
  due_date: string
  returned_at: string | null
  returned_by: UserBriefOut | null
  status: BorrowStatus
  notes: string | null
}

export interface BorrowCreate {
  book_id: number
  reader_id: number
  due_date?: string
  notes?: string
}

export interface BorrowQuery {
  page?: number
  page_size?: number
  status?: BorrowStatus
  book_id?: number
  reader_id?: number
  due_before?: string
}

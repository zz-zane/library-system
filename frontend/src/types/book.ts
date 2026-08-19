// 图书类型，契约见 docs/system-design.md 8.4
export interface BookOut {
  id: number
  title: string
  author: string
  isbn: string | null
  publisher: string | null
  publish_year: number | null
  category: string | null
  total_copies: number
  available_copies: number
  description: string | null
  created_at: string
  updated_at: string
}

export interface BookCreate {
  title: string
  author: string
  isbn?: string
  publisher?: string
  publish_year?: number
  category?: string
  total_copies?: number
  description?: string
}

export type BookUpdate = Partial<BookCreate>

export interface BookBriefOut {
  id: number
  title: string
  author: string
  isbn: string | null
}

export interface BookQuery {
  page?: number
  page_size?: number
  keyword?: string
  category?: string
  available_only?: boolean
}

// 读者类型，契约见 docs/system-design.md 8.5
export type ReaderStatus = 'active' | 'disabled'

export interface ReaderOut {
  id: number
  name: string
  phone: string | null
  email: string | null
  status: ReaderStatus
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ReaderCreate {
  name: string
  phone?: string
  email?: string
  notes?: string
}

export interface ReaderUpdate {
  name?: string
  phone?: string
  email?: string
  status?: ReaderStatus
  notes?: string
}

export interface ReaderBriefOut {
  id: number
  name: string
  phone: string | null
  email: string | null
}

export interface ReaderQuery {
  page?: number
  page_size?: number
  keyword?: string
  status?: ReaderStatus
}

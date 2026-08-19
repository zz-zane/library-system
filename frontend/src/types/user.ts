// 操作员类型，契约见 docs/system-design.md 8.3
export interface UserOut {
  id: number
  username: string
  display_name: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserBriefOut {
  id: number
  username: string
  display_name: string | null
}

export interface UserCreate {
  username: string
  password: string
  display_name?: string
}

export interface UserUpdate {
  display_name?: string
  password?: string
  is_active?: boolean
}

export interface UserQuery {
  page?: number
  page_size?: number
  username?: string
  is_active?: boolean
}

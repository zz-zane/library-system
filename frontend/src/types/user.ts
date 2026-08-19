// 操作员类型，契约见 docs/system-design.md 8.3
export interface UserOut {
  id: number
  username: string
  display_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// 共享 API 类型定义
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

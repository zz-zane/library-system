// 认证相关类型，契约见 docs/system-design.md 7.4 与 8.2
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenOut {
  access_token: string
  token_type: 'bearer'
}

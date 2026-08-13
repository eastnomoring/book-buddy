/**
 * 访问口令（Web 端）。
 * 后端 AUTH_TOKEN 环境变量开启后，所有 /api/* 需带 Authorization: Bearer <token>。
 * 口令存 localStorage，首次访问 / 401 时由 AccessGate 弹窗收集。
 */
import axios from 'axios'

const TOKEN_KEY = 'bb_auth_token'

export function getAuthToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/** 判断异常是否为后端 401（axios 错误或裸 fetch 的 HTTP 401 文本） */
export function isUnauthorized(e: unknown): boolean {
  if (axios.isAxiosError(e)) return e.response?.status === 401
  return e instanceof Error && e.message.includes('401')
}

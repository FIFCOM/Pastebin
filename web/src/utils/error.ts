import axios from 'axios'

export function extractErrorMessage(error: unknown, fallback = '操作失败'): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail
    }

    const message = error.message?.trim()
    if (message) return message
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }

  return fallback
}

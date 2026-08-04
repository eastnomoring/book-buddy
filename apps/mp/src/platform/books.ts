import {
  API_PATHS,
  mapBookInfo,
  mapUploadResult,
  PlatformError,
  type BookInfo,
  type BookUploadResult,
} from '@book-buddy/core'
import { getApiBase } from './config'

export function listBooks(): Promise<BookInfo[]> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getApiBase() + API_PATHS.BOOKS,
      method: 'GET',
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status < 200 || status >= 300) {
          reject(new PlatformError(`HTTP ${status}`))
          return
        }
        const data = res.data as Record<string, unknown>[]
        resolve(data.map(mapBookInfo))
      },
      fail: (err) => {
        reject(new PlatformError(err.errMsg || 'request failed', err))
      },
    })
  })
}


export function uploadBook(
  filePath: string,
  title?: string,
): Promise<BookUploadResult> {
  return new Promise((resolve, reject) => {
    const formData: Record<string, string> = {}
    if (title) formData.title = title

    wx.uploadFile({
      url: getApiBase() + API_PATHS.BOOKS_UPLOAD,
      filePath,
      name: 'file',
      formData,
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status < 200 || status >= 300) {
          reject(new PlatformError(`HTTP ${status}: ${res.data}`))
          return
        }
        try {
          const data = JSON.parse(res.data) as Record<string, unknown>
          resolve(mapUploadResult(data))
        } catch {
          reject(new PlatformError('上传响应解析失败'))
        }
      },
      fail: (err) => {
        reject(new PlatformError(err.errMsg || 'upload failed', err))
      },
    })
  })
}

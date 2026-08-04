/**
 * 小程序文件系统辅助：把临时文件读成裸 base64。
 */
import { PlatformError } from '@book-buddy/core'

export function readFileBase64(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().readFile({
      filePath,
      encoding: 'base64',
      success: (res) => {
        resolve(res.data as string)
      },
      fail: (err) => {
        reject(new PlatformError(err.errMsg || 'readFile failed', err))
      },
    })
  })
}

export function writeFileBase64(
  filePath: string,
  base64: string,
): Promise<void> {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().writeFile({
      filePath,
      data: base64,
      encoding: 'base64',
      success: () => resolve(),
      fail: (err) => reject(new PlatformError(err.errMsg || 'writeFile failed', err)),
    })
  })
}

export function removeFile(filePath: string): Promise<void> {
  return new Promise((resolve) => {
    wx.getFileSystemManager().unlink({
      filePath,
      success: () => resolve(),
      fail: () => resolve(),
    })
  })
}

/** 把工具结果图片（裸 base64）落到 USER_DATA_PATH，供 <image> 展示 */
export async function writeToolImage(
  base64: string,
  mediaType: string,
  idHint = 'img',
): Promise<string> {
  const ext = mediaType.includes('jpeg') || mediaType.includes('jpg')
    ? 'jpg'
    : mediaType.includes('svg')
      ? 'svg'
      : mediaType.includes('webp')
        ? 'webp'
        : 'png'
  const safe = idHint.replace(/[^\w-]/g, '').slice(0, 24) || 'img'
  const path = `${wx.env.USER_DATA_PATH}/tool_${safe}_${Date.now()}.${ext}`
  await writeFileBase64(path, base64)
  return path
}

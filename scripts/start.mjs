#!/usr/bin/env node
/**
 * Book Buddy 一键启动 CLI（零依赖，Node ≥ 18）
 *
 * 用法：
 *   node scripts/start.mjs              # 生产形态：后端 + 静态托管 dist（自动打开浏览器）
 *   node scripts/start.mjs --dev        # 开发形态：后端 --reload + vite dev（热更新）
 *   node scripts/start.mjs --desktop    # 桌面形态：后端 + vite dev + Tauri 壳
 *   node scripts/start.mjs --build      # 启动前先执行 pnpm build（仅生产形态）
 *
 * 选项：
 *   --port <n>        前端端口（默认 5173）
 *   --backend-port <n> 后端端口（默认 8000）
 *   --no-open         不自动打开浏览器
 *
 * Ctrl+C 会同时关闭所有子进程。
 */
import { spawn } from 'node:child_process'
import { createServer, request as httpRequest, get as httpGet } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { exec } from 'node:child_process'

const ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)), '..')
const BACKEND_DIR = join(ROOT, 'backend')
const WEB_DIST = join(ROOT, 'apps', 'web', 'dist')

const args = process.argv.slice(2)
const has = (flag) => args.includes(flag)
const option = (name, fallback) => {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? Number(args[i + 1]) : fallback
}

const MODE = has('--dev') ? 'dev' : has('--desktop') ? 'desktop' : 'prod'
const PORT = option('--port', 5173)
const BACKEND_PORT = option('--backend-port', 8000)
const OPEN_BROWSER = !has('--no-open')

const BACKEND_PYTHON = join(BACKEND_DIR, '.venv', 'bin', 'python')

/** @type {import('node:child_process').ChildProcess[]} */
const children = []

function run(name, command, cmdArgs, options = {}) {
  const child = spawn(command, cmdArgs, {
    stdio: 'inherit',
    detached: true,
    ...options,
  })
  child.on('error', (err) => {
    console.error(`[${name}] 启动失败: ${err.message}`)
  })
  children.push(child)
  return child
}

function startBackend({ reload = false } = {}) {
  const uvicornArgs = [
    '-m', 'uvicorn', 'main:app',
    '--host', '127.0.0.1',
    '--port', String(BACKEND_PORT),
  ]
  if (reload) uvicornArgs.push('--reload')
  return run('backend', BACKEND_PYTHON, uvicornArgs, { cwd: BACKEND_DIR })
}

function shutdown(code = 0) {
  for (const child of children) {
    try {
      // detached 子进程自成进程组，负 pid 杀掉整组（覆盖 uvicorn --reload 的孙子进程）
      process.kill(-child.pid, 'SIGTERM')
    } catch {
      /* 已退出 */
    }
  }
  process.exit(code)
}

process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))

function waitForBackend(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs
  return new Promise((resolvePromise, reject) => {
    const probe = () => {
      const req = httpGet(`http://127.0.0.1:${BACKEND_PORT}/health`, (res) => {
        res.resume()
        resolvePromise()
      })
      req.on('error', () => {
        if (Date.now() > deadline) {
          reject(new Error(`后端 ${timeoutMs / 1000}s 内未就绪（端口 ${BACKEND_PORT}）`))
        } else {
          setTimeout(probe, 500)
        }
      })
    }
    probe()
  })
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
}

function proxyApi(req, res) {
  const upstream = httpRequest(
    {
      host: '127.0.0.1',
      port: BACKEND_PORT,
      path: req.url,
      method: req.method,
      headers: { ...req.headers, host: `127.0.0.1:${BACKEND_PORT}` },
    },
    (upRes) => {
      res.writeHead(upRes.statusCode ?? 502, upRes.headers)
      upRes.pipe(res) // SSE 流式响应随管道直推
    },
  )
  upstream.on('error', (err) => {
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' })
    res.end(`后端不可达: ${err.message}`)
  })
  req.pipe(upstream)
}

async function serveStatic(req, res) {
  const urlPath = decodeURIComponent(new URL(req.url, 'http://x').pathname)
  let filePath = normalize(join(WEB_DIST, urlPath))
  if (!filePath.startsWith(WEB_DIST)) {
    res.writeHead(403).end('Forbidden')
    return
  }
  try {
    const info = await stat(filePath)
    if (info.isDirectory()) filePath = join(filePath, 'index.html')
  } catch {
    filePath = join(WEB_DIST, 'index.html') // SPA 回退
  }
  try {
    const body = await readFile(filePath)
    res.writeHead(200, {
      'content-type': MIME[extname(filePath)] ?? 'application/octet-stream',
    })
    res.end(body)
  } catch {
    res.writeHead(404).end('Not Found')
  }
}

function openBrowser(url) {
  const cmd =
    process.platform === 'darwin' ? 'open'
    : process.platform === 'win32' ? 'start'
    : 'xdg-open'
  exec(`${cmd} ${url}`)
}

async function main() {
  console.log(`[book-buddy] 模式: ${MODE}，后端端口: ${BACKEND_PORT}`)

  if (MODE === 'prod') {
    if (has('--build')) {
      console.log('[book-buddy] 先执行 pnpm build ...')
      const build = run('build', 'pnpm', ['build'], { cwd: ROOT })
      await new Promise((res, rej) => {
        build.on('exit', (code) => (code === 0 ? res() : rej(new Error(`pnpm build 失败（exit ${code}）`))))
      })
    }
    try {
      await stat(join(WEB_DIST, 'index.html'))
    } catch {
      console.error('[book-buddy] 未找到 apps/web/dist，请先运行 pnpm build（或加 --build 参数）')
      shutdown(1)
    }
  }

  startBackend({ reload: MODE === 'dev' })

  if (MODE === 'dev' || MODE === 'desktop') {
    run('web', 'pnpm', ['--filter', '@book-buddy/web', 'dev'], { cwd: ROOT })
    if (MODE === 'desktop') {
      // Tauri 壳读取 vite devUrl，需等 vite 起来；tauri 自身不拉起它
      run('desktop', 'pnpm', ['--filter', '@book-buddy/desktop', 'dev'], { cwd: ROOT })
    }
    await waitForBackend()
    console.log(`[book-buddy] 后端就绪 → http://127.0.0.1:${BACKEND_PORT}`)
    if (MODE === 'dev') {
      console.log(`[book-buddy] 前端 dev → http://localhost:${PORT}（vite 已配置 /api 代理）`)
      if (OPEN_BROWSER) openBrowser(`http://localhost:${PORT}`)
    }
    return // dev/desktop 形态由 vite/tauri 托管前端，常驻等待 Ctrl+C
  }

  // 生产形态：静态托管 + /api 反代
  const server = createServer((req, res) => {
    if (req.url?.startsWith('/api')) proxyApi(req, res)
    else serveStatic(req, res)
  })
  server.listen(PORT, async () => {
    await waitForBackend()
    const url = `http://localhost:${PORT}`
    console.log(`[book-buddy] 已启动 → ${url}（/api 反代到 :${BACKEND_PORT}）`)
    if (OPEN_BROWSER) openBrowser(url)
  })
}

main().catch((err) => {
  console.error(`[book-buddy] ${err.message}`)
  shutdown(1)
})

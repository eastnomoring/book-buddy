/**
 * 富文本渲染：Markdown + 数学公式（KaTeX）+ XSS 防护
 *
 * 渲染管线：
 *   原始文本
 *     → 预处理：把 $...$ / $$...$$ 数学公式占位，避免被 marked 吞掉
 *     → marked 解析为 HTML
 *     → 还原公式占位为 KaTeX HTML
 *     → DOMPurify 清洗，杜绝 XSS
 *
 * 这样既能渲染普林斯顿概率论里的 $E[X]=\int x f(x)\,dx$，
 * 也能处理普通的 **加粗**、`代码`、列表、代码块等。
 */
import { marked } from 'marked'
import katex from 'katex'
import DOMPurify from 'dompurify'

marked.setOptions({
  breaks: true,
  gfm: true,
})

// 占位符：Unicode 私用区，确保不会和正文冲突
const INLINE_MATH_TOKEN = '\uF8FF\uE000'
const BLOCK_MATH_TOKEN = '\uF8FF\uE001'

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderMath(latex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(latex, {
      displayMode,
      throwOnError: false,
      strict: false,
    })
  } catch {
    return `<code>${escapeHtml(latex)}</code>`
  }
}

// 公式占位还原表（同一次渲染内有效）
let placeholders: { token: string; html: string }[] = []

/**
 * 把文本中的数学公式替换为占位 token，返回占位后的文本与占位表。
 * 必须在 marked 解析之前调用——否则 $ 会被当成字面量或被吞掉。
 */
function extractMath(text: string): string {
  placeholders = []
  let result = text

  // 块级公式 $$...$$ 优先（贪婪匹配，跨行）
  result = result.replace(/\$\$([\s\S]+?)\$\$/g, (_m, latex: string) => {
    const html = renderMath(latex.trim(), true)
    placeholders.push({ token: BLOCK_MATH_TOKEN, html })
    return BLOCK_MATH_TOKEN
  })

  // 行内公式 $...$（单个 $ 且内部无换行）
  // 排除 \$ 转义和货币符号场景（要求 $ 后紧跟非空白、前一个字符非字母数字）
  result = result.replace(/(^|[^\w$])\$([^\n$]+?)\$/g, (_m, prefix: string, latex: string) => {
    const trimmed = latex.trim()
    if (!trimmed) return _m
    const html = renderMath(trimmed, false)
    placeholders.push({ token: INLINE_MATH_TOKEN, html })
    return `${prefix}${INLINE_MATH_TOKEN}`
  })

  return result
}

/** 把 marked 输出中的占位 token 还原为 KaTeX 渲染结果 */
function restoreMath(html: string): string {
  let i = 0
  // 私用区字符在正则里是字面量，用全局正则替换并逐个还原
  const blockRe = new RegExp(BLOCK_MATH_TOKEN, 'g')
  const inlineRe = new RegExp(INLINE_MATH_TOKEN, 'g')
  html = html.replace(blockRe, () => placeholders[i++]?.html || '')
  html = html.replace(inlineRe, () => placeholders[i++]?.html || '')
  return html
}

/**
 * 渲染为可直接 v-html 的安全 HTML。
 *
 * @param text LLM 原始输出
 */
export function renderRichText(text: string): string {
  if (!text) return ''
  const withoutMath = extractMath(text)
  const markedHtml = marked.parse(withoutMath, { async: false }) as string
  const restored = restoreMath(markedHtml)
  return DOMPurify.sanitize(restored, {
    ADD_TAGS: ['span'],
    ADD_ATTR: ['class'],
  })
}

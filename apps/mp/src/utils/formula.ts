import { getApiBase } from '../platform/config'

/** rich-text 节点（小程序 rich-text 组件的 nodes 项） */
export interface RichTextNode {
  type?: 'text' | 'node'
  name?: string
  attrs?: Record<string, string>
  text?: string
  children?: RichTextNode[]
}

/** 后端 Z3 公式渲染接口：GET {apiBase}/render/formula?latex=...&format=png */
export function formulaImageUrl(latex: string): string {
  return `${getApiBase()}/render/formula?latex=${encodeURIComponent(latex)}&format=png`
}

// $$...$$ 与 \[...\] 为块级公式；$...$ 与 \(...\) 为行内公式
const FORMULA_PATTERN =
  /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$[^$\n]+?\$)/g

/**
 * 把含 LaTeX 定界符的回答文本切成 rich-text 节点数组：
 * 普通文本段原样保留，公式段转为后端渲染的图片节点。
 * 流式输出期间未成对的定界符会按纯文本展示，闭合后自动变成图片。
 */
export function contentToNodes(content: string): RichTextNode[] {
  const nodes: RichTextNode[] = []
  let lastIndex = 0

  for (const match of content.matchAll(FORMULA_PATTERN)) {
    const raw = match[0]
    const index = match.index
    if (index > lastIndex) {
      nodes.push({ type: 'text', text: content.slice(lastIndex, index) })
    }

    let latex: string
    let block = false
    if (raw.startsWith('$$')) {
      latex = raw.slice(2, -2)
      block = true
    } else if (raw.startsWith('\\[')) {
      latex = raw.slice(2, -2)
      block = true
    } else if (raw.startsWith('\\(')) {
      latex = raw.slice(2, -2)
    } else {
      latex = raw.slice(1, -1)
    }

    nodes.push({
      name: 'img',
      attrs: {
        src: formulaImageUrl(latex.trim()),
        style: block
          ? 'display:block;margin:8px auto;max-width:100%;'
          : 'vertical-align:middle;',
      },
    })
    lastIndex = index + raw.length
  }

  if (lastIndex < content.length) {
    nodes.push({ type: 'text', text: content.slice(lastIndex) })
  }
  if (nodes.length === 0) {
    nodes.push({ type: 'text', text: '' })
  }
  return nodes
}

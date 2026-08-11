/**
 * TTS 朗读文本清洗与流式切句测试。
 *
 * spokenText：把 markdown/公式转成适合朗读的纯文本。
 * SentenceStreamer：把 LLM 增量文本按句读点切成完整句子，供逐句 TTS。
 *
 * 所有断言以源码当前实现的真实语义为准（含未覆盖的 markdown 语法）。
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spokenText, SentenceStreamer } from '../src/tts.js'

// ============ spokenText ============

test('spokenText: 空输入与纯空白返回空串', () => {
  assert.equal(spokenText(''), '')
  assert.equal(spokenText('   '), '')
})

test('spokenText: 行内公式 $...$ 替换为「公式」', () => {
  assert.equal(spokenText('结果是 $E=mc^2$ 对吧'), '结果是 公式 对吧')
  assert.equal(spokenText('$a$ 加 $b$'), '公式 加 公式')
})

test('spokenText: 块级公式 $$...$$ 替换为「，公式，」（可跨行）', () => {
  assert.equal(spokenText('$$\nE=mc^2\n$$'), '，公式，')
  assert.equal(spokenText('推导：$$x=1$$ 完毕'), '推导：，公式， 完毕')
})

test('spokenText: 代码块 ```...``` 替换为「，代码片段，」', () => {
  assert.equal(spokenText('看代码：```js\nlet x = 1\n```结束'), '看代码：，代码片段，结束')
})

test('spokenText: 行内代码反引号被移除，内容保留', () => {
  assert.equal(spokenText('`const x` 是代码'), 'const x 是代码')
})

test('spokenText: 加粗/标题/引用符号被移除', () => {
  assert.equal(spokenText('**重点**内容'), '重点内容')
  assert.equal(spokenText('## 章节标题'), '章节标题')
  assert.equal(spokenText('> 引用文字'), '引用文字')
})

test('spokenText: 链接保留文字、去掉 URL；图片朗读为「图片」', () => {
  assert.equal(spokenText('见[文档](https://example.com/p)'), '见文档')
  assert.equal(spokenText('结果 ![曲线图](https://example.com/a.png) 如上'), '结果 ，图片， 如上')
})

test('spokenText: 未闭合的 $ 不替换', () => {
  assert.equal(spokenText('价格是 $5 美元'), '价格是 $5 美元')
})

test('spokenText: 行内 $...$ 不跨行匹配', () => {
  assert.equal(spokenText('$第一行\n第二行$'), '$第一行\n第二行$')
})

// ============ SentenceStreamer ============

function createCollector() {
  const out: string[] = []
  const streamer = new SentenceStreamer((s) => out.push(s))
  return { out, streamer }
}

test('SentenceStreamer: 空输入不产出，空 buffer flush 不产出', () => {
  const { out, streamer } = createCollector()
  streamer.push('')
  assert.deepEqual(out, [])
  streamer.flush()
  assert.deepEqual(out, [])
})

test('SentenceStreamer: 带句读点的完整句立即产出（含句读点）', () => {
  const { out, streamer } = createCollector()
  streamer.push('你好。')
  assert.deepEqual(out, ['你好。'])
})

test('SentenceStreamer: 一个 chunk 内多句依次产出', () => {
  const { out, streamer } = createCollector()
  streamer.push('第一句。第二句!第三句?')
  assert.deepEqual(out, ['第一句。', '第二句!', '第三句?'])
})

test('SentenceStreamer: 跨 chunk 拼接成完整句', () => {
  const { out, streamer } = createCollector()
  streamer.push('你好')
  assert.deepEqual(out, [], '没有句读点时不产出')
  streamer.push('，世界。')
  assert.deepEqual(out, ['你好，世界。'])
})

test('SentenceStreamer: 句读点全集（。!?；; 与换行）都切句', () => {
  const { out, streamer } = createCollector()
  streamer.push('句号。叹号!问号?分号；英文;换行\n结束')
  streamer.flush()
  assert.deepEqual(out, ['句号。', '叹号!', '问号?', '分号；', '英文;', '换行', '结束'])
})

test('SentenceStreamer: 全角！？也是切句点', () => {
  const { out, streamer } = createCollector()
  streamer.push('真的吗？太好了！')
  assert.deepEqual(out, ['真的吗？', '太好了！'])
  streamer.flush()
  assert.deepEqual(out, ['真的吗？', '太好了！'])
})

test('SentenceStreamer: 无句读点的残余由 flush 产出', () => {
  const { out, streamer } = createCollector()
  streamer.push('有句号。残余部分')
  assert.deepEqual(out, ['有句号。'])
  streamer.flush()
  assert.deepEqual(out, ['有句号。', '残余部分'])
})

test('SentenceStreamer: flush 清空 buffer，重复 flush 不重复产出', () => {
  const { out, streamer } = createCollector()
  streamer.push('收尾句')
  streamer.flush()
  streamer.flush()
  assert.deepEqual(out, ['收尾句'])
})

test('SentenceStreamer: 仅含空白/换行的句被跳过不产出', () => {
  const { out, streamer } = createCollector()
  streamer.push('\n\n  \n')
  assert.deepEqual(out, [])
  streamer.flush()
  assert.deepEqual(out, [])
})

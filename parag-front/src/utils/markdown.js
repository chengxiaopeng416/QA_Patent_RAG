import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

marked.setOptions({
  breaks: true,
  gfm: true
})

// marked/gfm 规定"标题"与"列表第一项"前面必须空行才能正常识别。
// 部分 LLM 输出是"段落后直接跟标题/列表项"（中间无空行），这里做保守归一化：
// 只有当前行是标题、或是列表的第一项、且上一行不是空行时，才补一个空行，
// 避免打断列表内部或连续段落。最后把多余空行压缩回 \n\n。
function normalizeMarkdown(text) {
  const lines = text.split('\n')
  const out = []
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const isHeading = /^\s{0,3}#{1,6}\s/.test(line)
    const isListItem = /^\s{0,3}([-+*]|\d+\.)\s/.test(line)
    const prev = out.length ? out[out.length - 1] : '上'
    const prevEmpty = /^\s*$/.test(prev)
    const prevIsList = /^\s{0,3}([-+*]|\d+\.)\s/.test(prev)
    const needBlank = out.length > 0 && !prevEmpty && (isHeading || (isListItem && !prevIsList))
    if (needBlank) out.push('')
    out.push(line)
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n')
}

// 渲染 markdown 字符串为 html，代码块自动高亮
export function renderMarkdown(text) {
  if (!text) return ''
  const renderer = new marked.Renderer()
  const oldCode = renderer.code.bind(renderer)
  renderer.code = function (code, language) {
    const lang = language && hljs.getLanguage(language) ? language : 'plaintext'
    let highlighted
    try {
      highlighted = hljs.highlight(code, { language: lang }).value
    } catch (e) {
      highlighted = code
    }
    return `<pre class="hljs"><code>${highlighted}</code></pre>`
  }
  return marked.parse(normalizeMarkdown(text), { renderer })
}
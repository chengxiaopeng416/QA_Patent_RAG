<template>
  <el-container class="chat-container">
    <el-header class="chat-header">
      <span class="header-title"><i class="el-icon-s-opportunity" /> 技术专利文献智能分析</span>
      <div class="header-right">
        <div class="header-nav">
          <span class="nav-item" :class="{ active: $route.path === '/' }" @click="$router.push('/')">智能问答</span>
          <span class="nav-item" :class="{ active: $route.path === '/docs' }" @click="$router.push('/docs')">专利文档管理</span>
          <span v-if="isAdmin" class="nav-item" :class="{ active: $route.path === '/users' }" @click="$router.push('/users')">用户管理</span>
        </div>
        <user-dropdown />
      </div>
    </el-header>

    <el-main class="chat-main" :class="{ centered: !hasResult }">
      <!-- 装饰层 -->
      <div class="deco deco-a"></div>
      <div class="deco deco-b"></div>

      <!-- Hero 欢迎区 -->
      <div class="hero">
        <div class="hero-badge">
          <i class="el-icon-s-opportunity" /> 基于专利文献的智能分析助手
        </div>
        <h1 class="hero-title">您好，{{ username }} 👋</h1>
        <p class="hero-sub">
          基于 {{ docCount }} 篇专利文献的智能分析助手，支持横向对比、技术路线拆解与创新点挖掘。
        </p>
        <div class="chip-row">
          <span
            v-for="(q, i) in quickQuestions"
            :key="i"
            class="chip"
            @click="fillPrompt(q)"
          >{{ q }}</span>
        </div>
      </div>

      <!-- 提示词输入区 -->
      <el-card class="prompt-card" shadow="never">
        <div class="prompt-label">
          <span class="label-icon">🔍</span> 输入您的技术专利分析问题
        </div>
        <el-input
          v-model="prompt"
          type="textarea"
          class="prompt-input"
          :rows="3"
          :disabled="loading"
          placeholder="请输入您的技术专利分析需求。例如：对比Transformer和RNN在语音识别中的技术区别，并说明各自的应用场景"
        />
        <div class="prompt-actions">
          <el-button class="btn-cta" type="primary" :loading="loading" :disabled="!prompt || loading" @click="handleAsk">
            <i v-if="!loading" class="el-icon-s-platform" /> {{ loading ? '分析中…' : '提交分析' }}
          </el-button>
          <el-button v-if="loading" class="btn-stop" @click="handleStop">
            <i class="el-icon-video-pause" /> 停止
          </el-button>
        </div>
      </el-card>

      <!-- 结果区 -->
      <div v-loading="loading && !thinkingLog.length" element-loading-text="正在分析..." class="result-area">
        <!-- 思考过程：updates 事件 -->
        <el-card v-if="thinkingLog.length" class="thinking-card" shadow="never">
          <div slot="header" class="card-header">
            <span><i class="el-icon-loading" /> 思考过程</span>
          </div>
          <div class="thinking-body">
            <div v-for="(log, i) in thinkingLog" :key="i" class="thinking-item">
              <template v-if="log.type === 'strategy'">
                <div class="thinking-strategy">
                  <div class="strategy-title">🎯 检索策略：{{ log.retrievalTypes.join(' + ') }}</div>
                  <div class="strategy-reason">理由：{{ log.reasoning }}</div>
                  <div v-if="log.decomposition" class="strategy-sub">
                    子问题拆分：
                    <div v-for="(s, j) in log.subQueries" :key="j">- {{ s }}</div>
                  </div>
                </div>
              </template>
              <template v-else-if="log.type === 'tool_start'">
                <div class="tool-line">🔧 正在调用工具：<b>{{ log.name }}</b></div>
              </template>
              <template v-else-if="log.type === 'tool_end'">
                <div class="tool-line">✅ 工具执行完成：<b>{{ log.name }}</b></div>
              </template>
              <template v-else-if="log.type === 'todos'">
                <div class="todos-line">
                  <div v-for="(t, j) in log.todos" :key="j" class="todo-item"
                    :class="{ 'todo-done': t.status === 'completed' }">
                    <span v-if="t.status === 'completed'">✔</span>
                    <span v-else-if="t.status === 'in_progress'">🔄</span>
                    <span v-else>○</span> {{ t.content }}
                  </div>
                </div>
              </template>
            </div>
          </div>
        </el-card>

        <!-- 最终答案：answer 事件流式输出 -->
        <el-card v-if="answerDisplay" class="answer-card" shadow="never">
          <div slot="header" class="card-header">
            <span>💡 分析结果</span>
          </div>
          <div class="answer-body" v-html="answerHtml"></div>
        </el-card>

        <!-- 引用文档 -->
        <el-card v-if="references.length" class="ref-card" shadow="never">
          <div slot="header" class="card-header">
            <span>📎 引用文档</span>
          </div>
          <div v-for="(ref, i) in references" :key="i" class="ref-item">
            <b>{{ ref.source || ('doc_' + ref.doc_id) }}</b>
            <div class="ref-snippet">{{ ref.snippet }}</div>
          </div>
        </el-card>
      </div>
    </el-main>
  </el-container>
</template>

<script>
import { getToken, getUser } from '../utils/auth'
import { renderMarkdown } from '../utils/markdown'
import UserDropdown from '../components/UserDropdown.vue'
import { getProfile, getPatentList } from '../api'

export default {
  name: 'ChatView',
  components: { UserDropdown },
  data() {
    return {
      prompt: '',
      loading: false,
      isAdmin: false,       // 是否管理员，决定是否显示"用户管理"入口
      username: '用户',
      docCount: '多',       // 已索引专利文献数（用于 Hero 副标题）
      quickQuestions: [
        '新能源电池专利对比',
        'AGV导航技术分析',
        'Transformer与RNN技术区别',
        '语音识别应用场景'
      ],
      thinkingLog: [],      // 思考过程（strategy/tool_start/tool_end/todos）
      answerBuffer: '',     // answer 完整缓存
      answerDisplay: '',    // 打字机已显示部分
      answerHtml: '',
      references: [],       // done 事件的引用文档
      abortController: null,
      typewriterTimer: null
    }
  },
  computed: {
    typewriterInterval() {
      return 20
    },
    // 是否已有分析结果：决定 Hero 区是否垂直居中
    hasResult() {
      return !!(this.thinkingLog.length || this.answerDisplay || this.references.length)
    }
  },
  created() {
    const user = getUser()
    if (user && user.username) this.username = user.username
    this.checkAdmin()
    this.fetchDocCount()
  },
  destroyed() {
    this.stopTypewriter()
  },
  methods: {
    fillPrompt(q) {
      this.prompt = q
    },
    // 拉取已索引专利总数，用于 Hero 副标题
    async fetchDocCount() {
      try {
        const res = await getPatentList({ page: 1, page_size: 1 })
        if (res.data && res.data.total) this.docCount = res.data.total
      } catch (e) {
        // 静默失败，保留默认文案
      }
    },
    // 校验当前用户是否为管理员（仅管理员显示"用户管理"入口）
    async checkAdmin() {
      try {
        const res = await getProfile()
        this.isAdmin = (res.data && res.data.role) === '管理员'
      } catch (e) {
        this.isAdmin = false
      }
    },
    handleStop() {
      if (this.abortController) {
        this.abortController.abort()
      }
      this.loading = false
      this.stopTypewriter()
    },
    stopTypewriter() {
      if (this.typewriterTimer) {
        clearInterval(this.typewriterTimer)
        this.typewriterTimer = null
      }
    },
    handleAsk() {
      if (!this.prompt || this.loading) return
      // 重置上一轮状态
      this.thinkingLog = []
      this.answerBuffer = ''
      this.answerDisplay = ''
      this.answerHtml = ''
      this.references = []
      this.loading = true
      this.startFetch()
    },
    async startFetch() {
      this.abortController = new AbortController()
      const token = getToken()
      const query = encodeURIComponent(this.prompt.trim())
      try {
        const resp = await fetch('/api/chat/ask?query=' + query, {
          signal: this.abortController.signal,
          headers: { Authorization: 'Bearer ' + token }
        })
        if (!resp.ok || !resp.body) {
          throw new Error('HTTP ' + resp.status)
        }
        const reader = resp.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          // 按SSE帧切分处理
          let idx
          while ((idx = buffer.indexOf('\n\n')) >= 0) {
            const frame = buffer.slice(0, idx)
            buffer = buffer.slice(idx + 2)
            this.handleFrame(frame)
          }
        }
      } catch (e) {
        if (e.name !== 'AbortError') {
          this.$message.error('请求失败：' + e.message)
        }
      } finally {
        this.loading = false
        this.abortController = null
      }
    },
    handleFrame(frame) {
      let event = 'message'
      const dataLines = []
      frame.split('\n').forEach(line => {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      })
      if (!dataLines.length) return
      const payload = dataLines.join('\n')
      let data
      try {
        data = JSON.parse(payload)
      } catch (e) {
        data = payload
      }
      switch (event) {
        case 'strategy':
          this.thinkingLog.push({
            type: 'strategy',
            retrievalTypes: data.retrieval_types || [],
            reasoning: data.reasoning || '',
            decomposition: !!data.need_decomposition,
            subQueries: data.sub_queries_hint || []
          })
          break
        case 'todos':
          this.thinkingLog.push({ type: 'todos', todos: data })
          break
        case 'tool_start':
          this.thinkingLog.push({ type: 'tool_start', name: data.name })
          break
        case 'tool_end':
          this.thinkingLog.push({ type: 'tool_end', name: data.name })
          break
        case 'answer':
          // 流式累积，打字机效果逐字显示
          this.answerBuffer += data
          this.startTypewriter()
          break
        case 'done':
          this.references = data.references || []
          break
        case 'error':
          this.$message.error(data.message || '服务执行异常')
          break
        default:
          break
      }
    },
    // 打字机效果：定时将 answerBuffer 逐字转移到 answerDisplay
    startTypewriter() {
      if (this.typewriterTimer || this.answerDisplay === this.answerBuffer) {
        return
      }
      this.typewriterTimer = setInterval(() => {
        const target = this.answerBuffer.length
        const ok = Math.min(this.answerDisplay.length + 3, target)
        this.answerDisplay = this.answerBuffer.slice(0, ok)
        if (this.answerDisplay === this.answerBuffer) {
          this.stopTypewriter()
        }
      }, this.typewriterInterval)
    }
  },
  watch: {
    answerDisplay(newVal) {
      this.answerHtml = renderMarkdown(newVal)
      this.$nextTick(() => {
        const el = this.$el && this.$el.querySelector('.answer-body')
        if (el) el.scrollTop = el.scrollHeight
      })
    }
  }
}
</script>

<style scoped>
.chat-container { height: 100%; position: relative; overflow: hidden; }
.chat-main {
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
  position: relative;
  padding-top: 24px;
}
/* 无结果时：内容垂直居中，避免上方挤下方空 */
.chat-main.centered {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: calc(100vh - 60px);
}
.chat-main.centered .hero { padding: 8px 0 24px; }
.chat-main.centered .result-area { display: none; }

/* 极淡网格纹理，打破单调 */
.chat-container {
  background-image:
    linear-gradient(rgba(15, 23, 42, 0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.028) 1px, transparent 1px);
  background-size: 34px 34px;
}
/* 装饰层：抽象几何圆形，打破空旷感 */
.deco { position: fixed; border-radius: 50%; pointer-events: none; filter: blur(60px); opacity: 0.32; }
.deco-a { width: 340px; height: 340px; background: #bfdbfe; top: -120px; right: -90px; }
.deco-b { width: 260px; height: 260px; background: #bae6fd; bottom: 60px; left: -120px; }

/* Hero 区域 */
.hero { text-align: center; padding: 26px 0 22px; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: #e0f2fe; color: #0369a1;
  font-size: 13px; font-weight: 500;
  padding: 5px 14px; border-radius: 999px; margin-bottom: 14px;
}
.hero-title { font-size: 28px; font-weight: 700; color: #0f172a; margin: 0 0 10px; }
.hero-sub { font-size: 15px; color: #64748b; margin: 0 0 18px; }
.chip-row { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }
.chip {
  font-size: 13px; color: #1e3a5f;
  background: #fff; border: 1px solid #e2e8f0;
  padding: 7px 15px; border-radius: 999px; cursor: pointer;
  transition: all 0.2s ease; box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}
.chip:hover {
  background: #e0f2fe;
  color: #1e3a5f;
  border-color: #7dd3fc;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(56, 189, 248, 0.22);
}

/* 输入卡片 */
.prompt-card { margin-bottom: 16px; }
.prompt-label {
  font-size: 13px; font-weight: 600; color: #64748b;
  margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
}
.prompt-input >>> .el-textarea__inner {
  border-radius: 12px;
  padding: 16px 18px;
  font-size: 15px;
  line-height: 1.7;
}
.prompt-actions { margin-top: 14px; text-align: right; }
.btn-stop { margin-left: 10px; }
.result-area { min-height: 200px; }
.card-header { font-weight: bold; }
.thinking-card { margin-bottom: 16px; }
.thinking-item { margin: 6px 0; }
.thinking-strategy { background: #f4f7ff; border-radius: 6px; padding: 10px; }
.strategy-title { font-weight: bold; color: #1f3b73; }
.strategy-reason { font-size: 13px; color: #666; margin: 4px 0; }
.strategy-sub { font-size: 13px; color: #888; }
.tool-line { font-size: 13px; color: #555; }
.todo-item { font-size: 13px; color: #555; margin: 2px 0; }
.todo-done { color: #67c23a; }
.answer-card { margin-bottom: 16px; }
.answer-body {
  line-height: 1.7;
  font-size: 15px;
  max-height: 60vh;
  overflow-y: auto;
  word-break: break-word;
}
.answer-body >>> h1, .answer-body >>> h2,
.answer-body >>> h3, .answer-body >>> h4 {
  margin: 14px 0 8px;
  color: #1f3b73;
  font-weight: 600;
  line-height: 1.4;
}
.answer-body >>> h1 { font-size: 20px; border-bottom: 1px solid #e8ecf4; padding-bottom: 6px; }
.answer-body >>> h2 { font-size: 17px; }
.answer-body >>> h3 { font-size: 15px; }
.answer-body >>> p { margin: 6px 0; }
.answer-body >>> ul, .answer-body >>> ol { margin: 6px 0; padding-left: 22px; }
.answer-body >>> li { margin: 3px 0; }
.answer-body >>> blockquote {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 4px solid #b3c4e3;
  color: #666;
  background: #f7f9fc;
  border-radius: 0 4px 4px 0;
}
.answer-body >>> table {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  font-size: 14px;
}
.answer-body >>> th, .answer-body >>> td {
  border: 1px solid #e0e4ec;
  padding: 6px 10px;
  text-align: left;
}
.answer-body >>> th { background: #f2f5fb; font-weight: 600; }
.answer-body >>> tr:nth-child(even) td { background: #fafbfe; }
.answer-body >>> code {
  background: #f2f4f8;
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 13px;
}
.answer-body >>> pre {
  background: #f6f8fa;
  border: 1px solid #e5e8ef;
  border-radius: 6px;
  padding: 10px 12px;
  overflow-x: auto;
  font-size: 13px;
}
.answer-body >>> pre code { padding: 0; background: none; }
.answer-body >>> a { color: #1f3b73; }
.ref-card { margin-bottom: 16px; }
.ref-item { font-size: 13px; color: #444; border-bottom: 1px dashed #eee; padding: 8px 0; }
.ref-item:last-child { border-bottom: none; }
.ref-snippet { color: #888; font-size: 12px; margin-top: 4px; }
</style>
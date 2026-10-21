<template>
  <el-container class="docs-container">
    <el-header class="docs-header">
      <span class="header-title"><i class="el-icon-document" /> 专利文档管理</span>
      <div class="header-right">
        <div class="header-nav">
          <span class="nav-item" :class="{ active: $route.path === '/' }" @click="$router.push('/')">智能问答</span>
          <span class="nav-item" :class="{ active: $route.path === '/docs' }" @click="$router.push('/docs')">专利文档管理</span>
          <span v-if="isAdmin" class="nav-item" :class="{ active: $route.path === '/users' }" @click="$router.push('/users')">用户管理</span>
        </div>
        <user-dropdown />
      </div>
    </el-header>

    <el-main class="docs-main">
      <el-card shadow="never" class="docs-card">
        <!-- 统计卡片 -->
        <div class="stat-row">
          <div v-for="(s, i) in statCards" :key="i" class="stat-card" :style="{ background: s.bg }">
            <div class="stat-icon" :style="{ color: s.color }"><i :class="s.icon" /></div>
            <div class="stat-meta">
              <div class="stat-value num" :class="{ 'stat-empty': s.value === '—' }">{{ s.value }}</div>
              <div class="stat-label">{{ s.label }}</div>
            </div>
          </div>
        </div>

        <div slot="header" class="card-header">
          <div class="header-left">
            <el-button type="primary" size="small" :disabled="uploading" @click="$refs.uploadInput.click()">
              <i v-if="!uploading" class="el-icon-upload2" /> 上传专利文件
            </el-button>
            <input ref="uploadInput" type="file" accept=".md" style="display:none" @change="handleUpload" />
          </div>
        </div>

        <!-- 上传进度面板 -->
        <div v-if="uploading" class="upload-panel">
          <div class="upload-info">
            <i class="el-icon-document" /> {{ fileName }}
            <span class="upload-size">（{{ fileSize }}）</span>
          </div>
          <el-progress :percentage="uploadProgress" :status="progressStatus" />
          <div class="upload-tip">
            <template v-if="uploadProgress < 100">
              🚀 正在上传文件...（{{ uploadProgress }}%）
            </template>
            <template v-else>
              ⚙️ 正在创建索引，这一步需要离线向量化 + ES 关键词 + Neo4j 图谱，请耐心等待...
            </template>
          </div>
        </div>

        <el-table :data="records" v-loading="loading">
          <template slot="empty">
            <div class="empty-wrap">
              <i class="el-icon-folder-remove" />
              <p>暂无专利文档</p>
              <span>点击右上角"上传专利文件"添加第一篇专利</span>
            </div>
          </template>
          <el-table-column type="index" label="序号" width="64" />
          <el-table-column label="专利名称" min-width="220">
            <template slot-scope="scope">
              <a class="patent-name" @click="handleDetail(scope.row)">{{ scope.row.title || scope.row.patent_no }}</a>
              <div v-if="scope.row.title" class="patent-no">{{ scope.row.patent_no }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="applicant" label="申请人" min-width="150" show-overflow-tooltip>
            <template slot-scope="scope">
              <span class="text-secondary">{{ scope.row.applicant || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template slot-scope="scope">
              <span class="status-tag" :class="statusCls(scope.row.status)">{{ scope.row.status || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template slot-scope="scope">
              <el-tooltip content="查看文档" placement="top">
                <el-button class="op-btn" type="text" circle size="mini" @click="handleDetail(scope.row)">
                  <i class="el-icon-view" />
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除文档" placement="top">
                <el-button class="op-btn danger" type="text" circle size="mini" @click="handleDelete(scope.row)">
                  <i class="el-icon-delete" />
                </el-button>
              </el-tooltip>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          class="pager"
          background
          layout="prev, pager, next, total"
          :total="total"
          :page-size="pageSize"
          :current-page.sync="page"
          @current-change="loadList"
        />
      </el-card>

      <!-- 详情对话框 -->
      <el-dialog title="专利详情" :visible.sync="detailVisible" width="60%">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="专利名称">{{ current.patent_no }}</el-descriptions-item>
          <el-descriptions-item label="申请号">{{ current.patent_no }}</el-descriptions-item>
          <el-descriptions-item label="申请人">{{ current.applicant }}</el-descriptions-item>
          <el-descriptions-item label="发明人">{{ current.inventor }}</el-descriptions-item>
          <el-descriptions-item label="摘要">{{ current.abstract }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ current.status }}</el-descriptions-item>
        </el-descriptions>
      </el-dialog>
    </el-main>
  </el-container>
</template>

<script>
import { getPatentList, deletePatent, getPatentDetail, uploadPatent, getProfile } from '../api'
import UserDropdown from '../components/UserDropdown.vue'

export default {
  name: 'DocsView',
  components: { UserDropdown },
  data() {
    return {
      loading: false,
      isAdmin: false,
      records: [],
      total: 0,
      page: 1,
      pageSize: 10,
      detailVisible: false,
      current: {},
      uploading: false,
      fileName: '',
      fileSize: '',
      uploadProgress: 0,
      progressStatus: '',
      uploadStartTime: 0,
      statCards: [
        { label: '专利文档总数', value: '—', icon: 'el-icon-document', color: '#2563eb', bg: '#eff6ff' },
        { label: '申请机构数', value: '—', icon: 'el-icon-office-building', color: '#0891b2', bg: '#ecfeff' },
        { label: '技术领域数', value: '—', icon: 'el-icon-aim', color: '#7c3aed', bg: '#f5f3ff' },
        { label: '数据格式', value: 'Markdown', icon: 'el-icon-files', color: '#059669', bg: '#ecfdf5' }
      ]
    }
  },
  created() {
    this.loadList()
    this.checkAdmin()
    this.fetchStats()
  },
  methods: {
    // 状态标签：柔和配色
    statusCls(status) {
      if (status === '有效') return 's-valid'
      if (status === '失效') return 's-invalid'
      if (status === '审查中') return 's-exam'
      return 's-muted'
    },
    // 统计卡片：拉全量专利计算真实指标（后端单页上限 100，需翻页取全）
    async fetchStats() {
      try {
        const all = []
        let page = 1
        const PAGE_SIZE = 100
        while (true) {
          const res = await getPatentList({ page, page_size: PAGE_SIZE })
          const records = res.data.records || []
          all.push(...records)
          if (records.length < PAGE_SIZE) break
          page += 1
        }
        const total = all.length
        const applicants = new Set(all.map(r => (r.applicant || '').trim()).filter(Boolean))
        const fields = new Set(all.map(r => (r.ipc_code || '').split('/')[0].trim()).filter(Boolean))
        this.statCards[0].value = total
        this.statCards[1].value = applicants.size || '—'
        this.statCards[2].value = fields.size || '—'
      } catch (e) {
        // 静默失败，保留占位
      }
    },
    // 校验当前用户是否为管理员
    async checkAdmin() {
      try {
        const res = await getProfile()
        this.isAdmin = (res.data && res.data.role) === '管理员'
      } catch (e) {
        this.isAdmin = false
      }
    },
    async loadList() {
      this.loading = true
      try {
        const res = await getPatentList({ page: this.page, page_size: this.pageSize })
        this.records = res.data.records || []
        this.total = res.data.total || 0
      } catch (e) {
      } finally {
        this.loading = false
      }
    },
    async handleUpload(event) {
      const file = event.target.files && event.target.files[0]
      if (!file) return
      const formData = new FormData()
      formData.append('file', file)

      this.uploading = true
      this.fileName = file.name.replace(/_/g, ' ')
      this.fileSize = this.formatSize(file.size)
      this.uploadProgress = 0
      this.progressStatus = ''
      this.uploadStartTime = Date.now()

      try {
        const res = await uploadPatent(formData, e => {
          // axios 进度回调：上传文件阶段会从 0 走到 100
          if (e.total > 0) {
            this.uploadProgress = Math.min(100, Math.round((e.loaded / e.total) * 100))
          }
        })
        // 走到这里说明文件已传完、索引也建好了，进度拉到 100 并显示成功
        this.uploadProgress = 100
        this.progressStatus = 'success'
        if (res.message && res.message.indexOf('已存在') !== -1) {
          // 重复上传：后端不需建索引，直接友好提示
          this.$message.warning(res.message || '已存在该专利文档')
        } else {
          this.$message.success(res.message || '上传成功，索引已创建')
        }
        this.loadList()
      } catch (e) {
        this.progressStatus = 'exception'
        // 后端错误信息在 e.message（拦截器已弹窗），这里补一句友好的兜底提示
        this.$message.error((e && e.message) || '上传失败，请检查后端服务是否正常')
      } finally {
        this.uploading = false
        // 复用同一个 input 的 value 不可直接读取，需重置
        this.$refs.uploadInput.value = ''
        // 数秒后自动收起提示面板，避免一直占位
        setTimeout(() => {
          this.uploadProgress = 0
          this.progressStatus = ''
          this.fileName = ''
          this.fileSize = ''
        }, 2000)
      }
    },
    formatSize(bytes) {
      if (!bytes) return '0B'
      if (bytes < 1024) return bytes + 'B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
      return (bytes / (1024 * 1024)).toFixed(2) + 'MB'
    },
    async handleDetail(row) {
      const res = await getPatentDetail(row.id)
      this.current = res.data || row
      this.detailVisible = true
    },
    async handleDelete(row) {
      const confirm = await this.$confirm('确定删除该专利吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).catch(() => false)
      if (!confirm) return
      await deletePatent(row.id)
      this.$message.success('删除成功')
      this.loadList()
    }
  }
}
</script>

<style scoped>
.docs-container { height: 100%; }
.docs-main { max-width: 1000px; margin: 0 auto; width: 100%; }
.docs-card { margin-top: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; }
.pager { margin-top: 16px; text-align: right; }

/* 统计卡片 */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}
@media (max-width: 900px) { .stat-row { grid-template-columns: repeat(2, 1fr); } }
.stat-card {
  display: flex; align-items: center; gap: 12px;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}
.stat-icon {
  width: 42px; height: 42px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255, 255, 255, 0.75);
  font-size: 20px;
}
.stat-value { font-size: 22px; font-weight: 700; color: #0f172a; line-height: 1.2; }
.stat-value.stat-empty { color: #94a3b8 !important; font-weight: 500; }
.stat-label { font-size: 12px; color: #64748b; margin-top: 2px; }

/* 表格：压缩行高 + 悬停 */
.docs-card >>> .el-table td.el-table__cell { padding: 11px 0; }
.patent-name { color: #1e3a5f; font-weight: 600; cursor: pointer; transition: color 0.15s; }
.patent-name:hover { color: #2563eb; }
.patent-no { font-size: 12px; color: #94a3b8; margin-top: 2px; font-family: Consolas, monospace; }
.op-btn {
  font-size: 17px; color: #64748b; margin: 0 2px;
  transition: all 0.15s ease;
}
.op-btn:hover { color: #2563eb; background: #eff6ff; }
.op-btn.danger:hover { color: #dc2626; background: #fef2f2; }

/* 状态标签：柔和配色 */
.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}
.status-tag.s-valid { background: #dcfce7; color: #15803d; }
.status-tag.s-invalid { background: #fee2e2; color: #b91c1c; }
.status-tag.s-exam { background: #fef3c7; color: #b45309; }
.status-tag.s-muted { background: #e2e8f0; color: #475569; }

/* 空状态 */
.empty-wrap { padding: 34px 0; text-align: center; color: #94a3b8; }
.empty-wrap i { font-size: 42px; color: #cbd5e1; }
.empty-wrap p { font-size: 15px; font-weight: 600; color: #64748b; margin: 10px 0 4px; }
.empty-wrap span { font-size: 13px; }

.upload-panel {
  margin-top: 12px;
  padding: 16px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  background: #f8fafc;
}
.upload-info { font-size: 14px; color: #1e293b; font-weight: 600; margin-bottom: 10px; }
.upload-size { font-weight: normal; font-size: 12px; color: #94a3b8; margin-left: 6px; }
.upload-tip { margin-top: 10px; font-size: 13px; color: #475569; }
</style>
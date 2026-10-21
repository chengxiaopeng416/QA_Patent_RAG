<template>
  <el-container class="users-container">
    <el-header class="users-header">
      <span class="header-title"><i class="el-icon-s-management" /> 用户管理</span>
      <div class="header-right">
        <div class="header-nav">
          <span class="nav-item" :class="{ active: $route.path === '/' }" @click="$router.push('/')">智能问答</span>
          <span class="nav-item" :class="{ active: $route.path === '/docs' }" @click="$router.push('/docs')">专利文档管理</span>
          <span class="nav-item" :class="{ active: $route.path === '/users' }" @click="$router.push('/users')">用户管理</span>
        </div>
        <user-dropdown />
      </div>
    </el-header>

    <el-main class="users-main">
      <el-card shadow="never">
        <div slot="header" class="card-header">
          <div class="header-left">
            <el-input
              v-model="keyword"
              placeholder="搜索用户名 / 邮箱 / 机构"
              clearable
              style="width: 260px"
              prefix-icon="el-icon-search"
              @keyup.enter.native="handleSearch"
              @clear="handleSearch"
            />
            <el-button type="primary" size="small" @click="handleSearch">搜索</el-button>
          </div>
        </div>

        <el-table :data="records" v-loading="loading" stripe>
          <el-table-column type="index" label="序号" width="70" />
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="email" label="邮箱" min-width="180" />
          <el-table-column prop="organization" label="所属机构" min-width="160" show-overflow-tooltip />
          <el-table-column prop="role" label="角色" width="160">
            <template slot-scope="scope">
              <el-select v-if="scope.row._editing" v-model="scope.row.role" size="small" style="width: 110px">
                <el-option v-for="r in roleOptions" :key="r" :label="r" :value="r" />
              </el-select>
              <span v-else>{{ scope.row.role || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template slot-scope="scope">
              <template v-if="scope.row._editing">
                <el-button type="text" size="small" @click="saveRole(scope.row)">保存</el-button>
                <el-button type="text" size="small" @click="cancelEdit(scope.row)">取消</el-button>
              </template>
              <template v-else>
                <el-button type="text" size="small" @click="startEdit(scope.row)">改角色</el-button>
                <el-button type="text" size="small" style="color:#f56c6c"
                  :disabled="scope.row.username === myUsername"
                  @click="handleDelete(scope.row)">删除</el-button>
              </template>
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
    </el-main>
  </el-container>
</template>

<script>
import { listUsers, deleteUser, setUserRole, getProfile } from '../api'
import UserDropdown from '../components/UserDropdown.vue'
import { getUser } from '../utils/auth'

export default {
  name: 'Users',
  components: { UserDropdown },
  data() {
    return {
      loading: false,
      records: [],
      total: 0,
      page: 1,
      pageSize: 10,
      keyword: '',
      myUsername: '',
      roleOptions: ['研究员', '专利代理人', '审查员', '管理员']
    }
  },
  created() {
    const user = getUser()
    this.myUsername = (user && user.username) || ''
    // 校验是否管理员，非管理员无权访问
    this.checkAdmin()
  },
  methods: {
    async checkAdmin() {
      try {
        const res = await getProfile()
        const role = (res.data && res.data.role) || ''
        if (role !== '管理员') {
          this.$message.warning('无权限访问用户管理')
          this.$router.push('/')
          return
        }
        this.loadList()
      } catch (e) {
        this.$router.push('/')
      }
    },
    async loadList() {
      this.loading = true
      try {
        const res = await listUsers({ page: this.page, page_size: this.pageSize, keyword: this.keyword })
        // 用 _editing 标记行的编辑状态（非后端字段）
        this.records = (res.data.records || []).map(r => ({ ...r, _editing: false }))
        this.total = res.data.total || 0
      } catch (e) {
      } finally {
        this.loading = false
      }
    },
    handleSearch() {
      this.page = 1
      this.loadList()
    },
    startEdit(row) {
      row._editing = true
      row._oldRole = row.role
    },
    cancelEdit(row) {
      row.role = row._oldRole
      row._editing = false
    },
    async saveRole(row) {
      try {
        const res = await setUserRole(row.id, row.role)
        this.$message.success(res.message || '角色已更新')
        row._editing = false
      } catch (e) {
        // 拦截器已提示，恢复原角色
        row.role = row._oldRole
        row._editing = false
      }
    },
    async handleDelete(row) {
      const confirm = await this.$confirm(`确定删除用户「${row.username}」吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).catch(() => false)
      if (!confirm) return
      try {
        const res = await deleteUser(row.id)
        this.$message.success(res.message || '删除成功')
        this.loadList()
      } catch (e) {
      }
    }
  }
}
</script>

<style scoped>
.users-container { height: 100%; }
.users-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title { font-size: 18px; font-weight: 700; }
.users-main { max-width: 1000px; margin: 0 auto; width: 100%; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 8px; }
.pager { margin-top: 16px; text-align: right; }
</style>

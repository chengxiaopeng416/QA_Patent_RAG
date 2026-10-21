<template>
  <el-container class="profile-container">
    <el-header class="profile-header">
      <span class="header-title">编辑资料</span>
      <div class="header-right">
        <el-button type="text" @click="$router.push('/')">返回智能问答</el-button>
        <user-dropdown />
      </div>
    </el-header>

    <el-main class="profile-main">
      <el-card shadow="never" class="profile-card">
        <div slot="header" class="card-header">
          <div class="header-left">
            <div class="avatar-wrap">
              <div class="avatar">{{ avatarText }}</div>
              <div class="avatar-mask"><i class="el-icon-camera" /><span>更换头像</span></div>
            </div>
            <div>
              <div class="card-title">个人资料</div>
              <div class="card-tip">管理您的账户信息与分析偏好</div>
            </div>
          </div>
        </div>

        <el-form ref="profileForm" :model="form" label-position="top">
          <el-form-item label="用户名">
            <el-input v-model="form.username" disabled suffix-icon="el-icon-lock" />
            <div class="field-hint">用户名不可修改，如需变更请联系管理员</div>
          </el-form-item>
          <el-form-item v-if="editing" label="原密码" prop="old_password">
            <el-input v-model="form.old_password" type="password" placeholder="请输入原密码以确认修改" show-password
              @keyup.enter.native="handleSave" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" :disabled="!editing" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="所属机构">
            <el-input v-model="form.organization" :disabled="!editing" placeholder="请输入所属机构/公司" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="form.role" :disabled="!editing" placeholder="请选择角色" style="width: 100%">
              <el-option v-for="r in roleOptions" :key="r" :label="r" :value="r" />
            </el-select>
          </el-form-item>
          <el-form-item label="研究领域">
            <el-input v-model="form.research_field" :disabled="!editing" placeholder="请输入研究领域" />
          </el-form-item>
          <el-form-item label="专利关注方向">
            <el-input v-model="form.patent_focus" :disabled="!editing" placeholder="请输入专利关注方向（IPC分类号/技术领域）" />
          </el-form-item>
        </el-form>

        <div v-if="editing" class="card-footer">
          <el-button class="btn-outline" @click="cancelEdit">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <i class="el-icon-check" /> 保存修改
          </el-button>
        </div>
        <div v-else class="card-footer">
          <el-button type="primary" plain :disabled="editing" @click="startEdit">
            <i class="el-icon-edit-outline" /> 编辑资料
          </el-button>
        </div>
      </el-card>
    </el-main>
  </el-container>
</template>

<script>
import { getProfile, updateProfile } from '../api'
import UserDropdown from '../components/UserDropdown.vue'

export default {
  name: 'Profile',
  components: { UserDropdown },
  data() {
    return {
      loading: false,
      saving: false,
      editing: false, // false=只读展示；true=可编辑
      form: {
        username: '',
        email: '',
        organization: '',
        role: '',
        research_field: '',
        patent_focus: '',
        old_password: '' // 二次验证用，仅编辑时填
      },
      rules: {
        old_password: [{ required: true, message: '请先输入原密码以确认修改', trigger: 'blur' }]
      },
      roleOptions: ['研究员', '专利代理人', '审查员', '管理员']
    }
  },
  computed: {
    // 头像文字：取用户名首字符
    avatarText() {
      const name = this.form.username || '用'
      return name.charAt(0).toUpperCase()
    }
  },
  created() {
    this.loadProfile()
  },
  methods: {
    // 取消编辑：恢复原始数据
    cancelEdit() {
      this.form = { ...this.original }
      this.editing = false
    },
    // 从后端 /auth/me 拿到 t_user 里的完整资料
    async loadProfile() {
      this.loading = true
      try {
        const res = await getProfile()
        const data = res.data || {}
        this.form = {
          username: data.username || '',
          email: data.email || '',
          organization: data.organization || '',
          role: data.role || '',
          research_field: data.research_field || '',
          patent_focus: data.patent_focus || '',
          old_password: ''
        }
        // 拿到原始备份，用于"未保存时不改库"的对比
        this.original = { ...this.form }
      } catch (e) {
        // 拦截器已提示
      } finally {
        this.loading = false
      }
    },
    // 点击"编辑"：允许修改所有字段
    startEdit() {
      this.editing = true
      this.form.old_password = ''
    },
    // 点击"保存"：对比变化，提交前需二次验证原密码
    async handleSave() {
      const changed = {}
      Object.keys(this.form).forEach(key => {
        if (key === 'username' || key === 'old_password') return // 用户名与密码非资料字段
        if (this.form[key] !== this.original[key]) {
          changed[key] = this.form[key]
        }
      })
      if (Object.keys(changed).length === 0) {
        this.$message.info('未检测到修改')
        this.editing = false
        return
      }
      // 二次验证：原密码必填
      if (!this.form.old_password) {
        this.$message.warning('请先输入原密码以确认修改')
        return
      }
      this.saving = true
      try {
        const res = await updateProfile({
          old_password: this.form.old_password,
          ...changed
        })
        this.$message.success(res.message || '更新成功')
        // 保存成功后：更新本地备份，退出编辑态
        this.original = { ...this.form }
        this.editing = false
      } catch (e) {
        // 拦截器已提示（如原密码错误会提示1006），保留编辑态让用户修正
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style scoped>
.profile-container { height: 100%; }
.profile-main { max-width: 720px; margin: 0 auto; width: 100%; }
.profile-card { margin-top: 24px; }
.card-header { display: flex; align-items: center; }
.header-left { display: flex; align-items: center; gap: 16px; }
.avatar-wrap { position: relative; flex-shrink: 0; cursor: pointer; border-radius: 50%; }
.avatar {
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #1e3a5f, #2563eb);
  color: #fff; font-size: 24px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  border: 3px solid #e0f2fe;
}
.avatar-mask {
  position: absolute; inset: 0; border-radius: 50%;
  background: rgba(2, 8, 23, 0.45);
  color: #fff; font-size: 11px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
  opacity: 0; transition: opacity 0.2s ease;
}
.avatar-mask i { font-size: 17px; }
.avatar-wrap:hover .avatar-mask { opacity: 1; }
.card-title { font-size: 18px; font-weight: 700; color: #0f172a; }
.card-tip { font-size: 12px; color: #94a3b8; margin-top: 4px; }
.field-hint { font-size: 12px; color: #94a3b8; margin-top: 4px; }
.card-footer {
  display: flex; justify-content: flex-end; align-items: center; gap: 12px;
  padding-top: 16px; margin-top: 8px;
  border-top: 1px solid #eef2f7;
}
.btn-outline.el-button {
  border: 1px solid #cbd5e1; color: #475569; background: #fff;
}
</style>

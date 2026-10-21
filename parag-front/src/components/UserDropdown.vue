<template>
  <div class="user-dropdown-wrap">
    <el-dropdown trigger="click" @command="handleCommand">
      <span class="user-name">
        <span class="user-avatar">{{ avatarText }}</span>
        <span class="user-nick">{{ username }}</span>
        <i class="el-icon-arrow-down el-icon--right" />
      </span>
      <el-dropdown-menu slot="dropdown">
        <div class="menu-head">
          <div class="menu-avatar">{{ avatarText }}</div>
          <div class="menu-meta">
            <div class="menu-name">{{ username }}</div>
            <div class="menu-tip">技术专利文献分析系统</div>
          </div>
        </div>
        <el-dropdown-item command="profile" icon="el-icon-edit-outline">编辑资料</el-dropdown-item>
        <el-dropdown-item command="password" icon="el-icon-key">修改密码</el-dropdown-item>
        <el-dropdown-item command="logout" icon="el-icon-switch-button" divided>退出登录</el-dropdown-item>
        <el-dropdown-item command="delete" icon="el-icon-delete" class="danger" divided>注销账号</el-dropdown-item>
      </el-dropdown-menu>
    </el-dropdown>

    <!-- 修改密码对话框（顶部标签布局 + 密码强度条） -->
    <el-dialog :visible.sync="pwdVisible" width="440px" class="pwd-dialog" :close-on-click-modal="false" @closed="resetPwd">
      <span slot="title" class="dialog-title">
        <i class="el-icon-key" /> 修改密码</span>
      <div class="dialog-accent"></div>
      <el-form ref="pwdForm" :model="pwdForm" :rules="pwdRules" label-position="top">
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="pwdForm.oldPassword" type="password" placeholder="请输入原密码" prefix-icon="el-icon-lock" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" placeholder="请输入新密码（6-32 位）" prefix-icon="el-icon-lock" show-password />
          <div class="strength-bar">
            <span
              v-for="n in 4"
              :key="n"
              class="seg"
              :class="[{ on: n <= strengthLevel }, strengthCls]"
            ></span>
            <span class="strength-label" :class="strengthCls">{{ strengthText }}</span>
          </div>
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="pwdForm.confirmPassword" type="password" placeholder="请再次输入新密码" prefix-icon="el-icon-lock" show-password
            @keyup.enter.native="handleChangePassword" />
        </el-form-item>
      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="handleChangePassword">确定</el-button>
      </div>
    </el-dialog>

    <!-- 注销账号对话框 -->
    <el-dialog title="注销账号" :visible.sync="delVisible" width="460px" :close-on-click-modal="false">
      <el-alert type="warning" :closable="false" show-icon class="del-alert"
        title="注销后将无法再登录，且该账号上传的专利信息不受影响。此操作不可撤销，请谨慎操作。" />
      <el-form ref="delForm" :model="delForm" :rules="delRules" label-position="top">
        <el-form-item label="登录密码" prop="password">
          <el-input v-model="delForm.password" type="password" placeholder="请输入登录密码以确认" prefix-icon="el-icon-lock" show-password
            @keyup.enter.native="handleDelete" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="delVisible = false">取消</el-button>
        <el-button type="danger" :loading="delLoading" @click="handleDelete">确定注销</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { getUser, removeToken } from '../utils/auth'
import { changePassword, deleteAccount } from '../api'

export default {
  name: 'UserDropdown',
  data() {
    const validateConfirm = (rule, value, callback) => {
      if (value !== this.pwdForm.newPassword) {
        callback(new Error('两次输入的新密码不一致'))
      } else {
        callback()
      }
    }
    return {
      pwdVisible: false,
      pwdLoading: false,
      pwdForm: { oldPassword: '', newPassword: '', confirmPassword: '' },
      pwdRules: {
        oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
        newPassword: [
          { required: true, message: '请输入新密码', trigger: 'blur' },
          { min: 6, max: 32, message: '密码长度为 6-32 个字符', trigger: 'blur' }
        ],
        confirmPassword: [{ required: true, validator: validateConfirm, trigger: 'blur' }]
      },
      delVisible: false,
      delLoading: false,
      delForm: { password: '' },
      delRules: {
        password: [{ required: true, message: '请输入登录密码', trigger: 'blur' }]
      }
    }
  },
  computed: {
    username() {
      const user = getUser()
      return (user && user.username) || '未登录'
    },
    // 头像文字：取用户名首字符大写
    avatarText() {
      const name = this.username
      return name === '未登录' ? '?' : name.charAt(0).toUpperCase()
    },
    // 密码强度评分 0-100
    strengthScore() {
      const p = this.pwdForm.newPassword || ''
      if (!p) return 0
      let score = 0
      if (p.length >= 6) score += 25
      if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score += 25
      if (/\d/.test(p)) score += 25
      if (/[^A-Za-z0-9]/.test(p)) score += 25
      return score
    },
    // 分段强度条：1-4 段
    strengthLevel() {
      const s = this.strengthScore
      return s === 0 ? 0 : Math.max(1, Math.round(s / 25))
    },
    strengthCls() {
      const l = this.strengthLevel
      if (l <= 2) return 'weak'
      if (l === 3) return 'medium'
      return 'strong'
    },
    strengthText() {
      const l = this.strengthLevel
      if (l === 0) return ''
      if (l <= 2) return '弱'
      if (l === 3) return '中'
      return '强'
    }
  },
  methods: {
    handleCommand(command) {
      if (command === 'profile') {
        this.$router.push('/profile')
      } else if (command === 'password') {
        this.pwdVisible = true
      } else if (command === 'logout') {
        removeToken()
        this.$message.success('已退出登录')
        this.$router.push('/login')
      } else if (command === 'delete') {
        this.delVisible = true
      }
    },
    // 关闭修改密码框时清空表单和校验
    resetPwd() {
      this.pwdForm = { oldPassword: '', newPassword: '', confirmPassword: '' }
      if (this.$refs.pwdForm) this.$refs.pwdForm.clearValidate()
    },
    // 提交修改密码
    handleChangePassword() {
      this.$refs.pwdForm.validate(async valid => {
        if (!valid) return
        this.pwdLoading = true
        try {
          const res = await changePassword({
            old_password: this.pwdForm.oldPassword,
            new_password: this.pwdForm.newPassword
          })
          this.$message.success(res.message || '密码修改成功')
          this.pwdVisible = false
          // 修改密码后：后端已强制该用户所有旧token下线，前端同步登出
          removeToken()
          this.$router.push('/login')
        } catch (e) {
          // 错误已由拦截器统一提示
        } finally {
          this.pwdLoading = false
        }
      })
    },
    // 提交注销账号
    handleDelete() {
      this.$refs.delForm.validate(async valid => {
        if (!valid) return
        this.delLoading = true
        try {
          const res = await deleteAccount({ password: this.delForm.password })
          this.$message.success(res.message || '账号已注销')
          this.delVisible = false
          // 注销成功回到登录页
          removeToken()
          this.$router.push('/login')
        } catch (e) {
          // 错误已由拦截器统一提示
        } finally {
          this.delLoading = false
        }
      })
    }
  }
}
</script>

<style scoped>
.user-dropdown-wrap {
  display: inline-flex;
  align-items: center;
}
.user-name {
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  padding: 4px 10px;
  border-radius: 999px;
  transition: background 0.2s ease;
}
.user-name:hover { background: rgba(255, 255, 255, 0.14); }
.user-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg, #38bdf8, #2563eb);
  color: #fff; font-size: 13px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}
.user-nick { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 下拉菜单头部 */
.menu-head {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; margin-bottom: 6px;
  border-bottom: 1px solid #eef2f7;
}
.menu-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  background: linear-gradient(135deg, #38bdf8, #2563eb);
  color: #fff; font-size: 18px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.menu-name { font-size: 14px; font-weight: 600; color: #0f172a; line-height: 1.4; }
.menu-tip { font-size: 12px; color: #94a3b8; }

/* 弹窗顶部彩色细线 */
.dialog-accent {
  height: 3px;
  background: linear-gradient(90deg, #1e3a5f, #2563eb, #38bdf8);
  margin: -30px -20px 18px;
  border-radius: 999px;
}
.dialog-title { font-size: 15px; font-weight: 600; color: #0f172a; }
.dialog-title i { color: #2563eb; margin-right: 6px; }
.del-alert { margin-bottom: 14px; }

/* 弹窗表单：压缩纵向间距 16 → 12 */
.pwd-dialog >>> .el-form-item { margin-bottom: 12px; }
.pwd-dialog >>> .el-form-item__label { line-height: 1; padding-bottom: 6px; }
.dialog-footer .el-button ~ .el-button { margin-left: 12px; }

/* 分段式密码强度条：4 段 */
.strength-bar { margin-top: 8px; display: flex; align-items: center; gap: 6px; }
.seg {
  flex: 1; height: 6px; border-radius: 999px;
  background: #e2e8f0;
  transition: background 0.2s ease;
}
.seg.on.weak { background: #f87171; }
.seg.on.medium { background: #fbbf24; }
.seg.on.strong { background: #34d399; }
.strength-label { font-size: 12px; min-width: 2em; text-align: right; }
.strength-label.weak { color: #f87171; }
.strength-label.medium { color: #f59e0b; }
.strength-label.strong { color: #10b981; }
</style>

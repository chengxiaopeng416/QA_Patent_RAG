<template>
  <div class="login-container">
    <div class="deco deco-a"></div>
    <div class="deco deco-b"></div>
    <div class="login-grid"></div>

    <el-card class="login-card">
      <div class="login-head">
        <div class="login-logo">
          <i class="el-icon-s-opportunity" />
        </div>
        <h2 class="login-title">技术专利文献分析系统</h2>
        <p class="login-sub">基于专利文献的智能分析助手</p>
      </div>

      <!-- 登录表单 -->
      <el-form v-if="mode === 'login'" ref="loginForm" :model="form" :rules="rules" label-width="0">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="el-icon-user" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="el-icon-lock" show-password
            @keyup.enter.native="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
        <div class="switch-line">
          没有账号？<a @click="switchMode('register')">立即注册</a>
        </div>
      </el-form>

      <!-- 注册表单 -->
      <el-form v-else ref="regForm" :model="regForm" :rules="regRules" label-width="0">
        <el-form-item prop="username">
          <el-input v-model="regForm.username" placeholder="请输入用户名" prefix-icon="el-icon-user" clearable />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="regForm.email" placeholder="请输入邮箱" prefix-icon="el-icon-message" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="regForm.password" type="password" placeholder="请输入密码" prefix-icon="el-icon-lock" show-password />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input v-model="regForm.confirmPassword" type="password" placeholder="请再次输入密码" prefix-icon="el-icon-lock" show-password
            @keyup.enter.native="handleRegister" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" :loading="loading" @click="handleRegister">
            注 册
          </el-button>
        </el-form-item>
        <div class="switch-line">
          已有账号？<a @click="switchMode('login')">返回登录</a>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { login, register } from '../api'
import { setToken, setUser } from '../utils/auth'

export default {
  name: 'Login',
  data() {
    const validateConfirm = (rule, value, callback) => {
      if (value !== this.regForm.password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    }
    return {
      loading: false,
      mode: 'login',
      form: {
        username: '',
        password: ''
      },
      regForm: {
        username: '',
        email: '',
        password: '',
        confirmPassword: ''
      },
      rules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
      },
      regRules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        email: [
          { required: true, message: '请输入邮箱', trigger: 'blur' },
          { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, max: 32, message: '密码长度为 6-32 个字符', trigger: 'blur' }
        ],
        confirmPassword: [{ required: true, validator: validateConfirm, trigger: 'blur' }]
      }
    }
  },
  methods: {
    // 切换登录 / 注册
    switchMode(mode) {
      this.mode = mode
      this.loading = false
    },
    handleLogin() {
      this.$refs.loginForm.validate(async valid => {
        if (!valid) return
        this.loading = true
        try {
          const res = await login(this.form)
          // 后台返回的 token 保存到缓存
          setToken(res.data)
          setUser({ username: this.form.username })
          this.$message.success('登录成功')
          this.$router.push('/')
        } catch (e) {
          // 错误已由拦截器统一提示
        } finally {
          this.loading = false
        }
      })
    },
    handleRegister() {
      this.$refs.regForm.validate(async valid => {
        if (!valid) return
        this.loading = true
        try {
          const res = await register({
            username: this.regForm.username,
            email: this.regForm.email,
            password: this.regForm.password
          })
          this.$message.success('注册成功，请登录')
          // 注册成功后切回登录页，并预填账号
          this.form.username = this.regForm.username
          this.form.password = ''
          this.switchMode('login')
        } catch (e) {
          // 错误已由拦截器统一提示
        } finally {
          this.loading = false
        }
      })
    }
  }
}
</script>

<style scoped>
.login-container {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 55%, #1d4ed8 130%);
  position: relative;
  overflow: hidden;
}
/* 装饰：模糊光斑 + 网格，打破空旷感 */
.deco { position: absolute; border-radius: 50%; filter: blur(70px); pointer-events: none; }
.deco-a { width: 480px; height: 480px; background: rgba(56, 189, 248, 0.28); top: -140px; left: -120px; }
.deco-b { width: 420px; height: 420px; background: rgba(37, 99, 235, 0.35); bottom: -160px; right: -110px; }
.login-grid {
  position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px);
  background-size: 44px 44px;
}
.login-card {
  width: 400px;
  padding: 26px 24px;
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(2, 8, 23, 0.35) !important;
  position: relative; z-index: 1;
}
.login-head { display: flex; flex-direction: column; align-items: center; margin-bottom: 24px; }
.login-logo {
  width: 56px; height: 56px; border-radius: 14px; margin-bottom: 12px;
  background: linear-gradient(135deg, #1e3a5f, #2563eb);
  color: #fff; font-size: 28px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35);
}
.login-title { text-align: center; color: #0f172a; margin: 0; font-size: 20px; font-weight: 700; }
.login-sub { text-align: center; color: #94a3b8; font-size: 13px; margin: 6px 0 0; }
.login-card .el-button--primary { width: 100%; height: 40px; font-size: 15px; letter-spacing: 4px; }
.switch-line {
  text-align: center;
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}
.switch-line a {
  color: #2563eb;
  cursor: pointer;
  font-weight: 500;
  margin-left: 4px;
}
.switch-line a:hover { text-decoration: underline; }
</style>
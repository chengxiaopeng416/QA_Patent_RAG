import axios from 'axios'
import { Message } from 'element-ui'
import { getToken, removeToken } from './auth'
import router from '../router'

const service = axios.create({
  baseURL: '/api',
  timeout: 60000
})

// 请求拦截器：除登录/注册接口外，统一携带 token
service.interceptors.request.use(config => {
  const isAuth = config.url &&
    (config.url.indexOf('/auth/login') !== -1 || config.url.indexOf('/auth/register') !== -1)
  if (!isAuth) {
    const token = getToken()
    if (token) {
      config.headers.Authorization = 'Bearer ' + token
    }
  }
  return config
}, error => Promise.reject(error))

// 响应拦截器：统一处理业务码和登录过期
service.interceptors.response.use(response => {
  const res = response.data
  if (res && res.code !== 200) {
    if (res.code === 4002 || res.code === 4003) {
      removeToken()
      router.push('/login')
      Message.error('登录已过期，请重新登录')
      return Promise.reject(new Error(res.message))
    }
    Message.error(res.message || '请求失败')
    return Promise.reject(new Error(res.message))
  }
  return res
}, error => {
  if (error.response && error.response.status === 401) {
    removeToken()
    router.push('/login')
    Message.error('登录已过期，请重新登录')
  } else if (error.response) {
    // 后端返回了 HTTP 错误（如 FastAPI 422 校验失败），尽量显示具体原因
    const d = error.response.data
    let msg = (d && (d.detail || d.message)) || ('请求失败：' + error.response.status)
    if (typeof msg !== 'string') msg = JSON.stringify(msg)
    Message.error(msg)
  } else {
    Message.error('网络异常：' + (error.message || ''))
  }
  return Promise.reject(error)
})

export default service
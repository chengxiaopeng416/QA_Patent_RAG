import request from '../utils/request'

// 用户登录
export function login(data) {
  return request.post('/auth/login', data)
}

// 用户注册
export function register(data) {
  return request.post('/auth/register', data)
}

// 获取当前登录用户的资料
export function getProfile() {
  return request.get('/auth/me')
}

// 更新当前登录用户的资料
export function updateProfile(data) {
  return request.put('/auth/me', data)
}

// 修改密码
export function changePassword(data) {
  return request.put('/auth/password', data)
}

// 注销账号
export function deleteAccount(data) {
  return request.delete('/auth/me', { data })
}

// 管理员：用户列表（分页/搜索）
export function listUsers(params) {
  return request.get('/auth/users', { params })
}

// 管理员：修改用户角色
export function setUserRole(userId, role) {
  return request.put('/auth/users/' + userId + '/role', { role })
}

// 管理员：删除用户
export function deleteUser(userId) {
  return request.delete('/auth/users/' + userId)
}

// 非流式问答
export function invokeChat(data) {
  return request.post('/chat/invoke', data)
}

// 专利文档列表
export function getPatentList(params) {
  return request.get('/docs', { params })
}

// 专利文档详情
export function getPatentDetail(id) {
  return request.get('/docs/' + id)
}

// 删除专利文档
export function deletePatent(id) {
  return request.delete('/docs/' + id)
}

// 专利文件上传（创建索引）：接口地址封装在此文件，不在页面中直接暴露
// onUploadProgress：axios 上传进度回调，用于页面展示进度条
export function uploadPatent(formData, onUploadProgress) {
  return request.post('/admin/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  })
}
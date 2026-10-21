import Vue from 'vue'
import Router from 'vue-router'
import { getToken } from '../utils/auth'

Vue.use(Router)

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    name: 'Chat',
    component: () => import('../views/ChatView.vue'),
    meta: { title: '专利智能问答' }
  },
  {
    path: '/docs',
    name: 'Docs',
    component: () => import('../views/DocsView.vue'),
    meta: { title: '专利文档管理' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { title: '编辑资料' }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('../views/Users.vue'),
    meta: { title: '用户管理' }
  }
]

const router = new Router({
  mode: 'history',
  routes
})

// 导航守卫：未登录访问任何页面时，强制跳转到登录页
router.beforeEach((to, from, next) => {
  if (to.path === '/login') {
    next()
    return
  }
  if (!getToken()) {
    next('/login')
    return
  }
  next()
})

export default router
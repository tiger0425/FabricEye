/**
 * Vue Router 路由配置
 * 定义应用的路由规则和页面导航
 */
import { createRouter, createWebHistory } from 'vue-router'

// 导入布局组件（需要先创建）
import Layout from '@/components/common/Layout.vue'

// 导入页面视图组件
import Home from '@/views/Home.vue'
import Rolls from '@/views/Rolls.vue'
import Monitor from '@/views/Monitor.vue'
import Reports from '@/views/Reports.vue'
import Settings from '@/views/Settings.vue'

/**
 * 路由配置数组
 * 每个对象代表一个路由规则
 */
const routes = [
  {
    // 根路径 - 重定向到首页
    path: '/',
    redirect: '/home'
  },
  {
    // 布局路由 - 包含侧边栏和头部的基础布局
    path: '/',
    component: Layout,
    children: [
      {
        // 首页
        path: 'home',
        name: 'Home',
        component: Home,
        meta: {
          title: '首页',
          icon: 'HomeFilled'
        }
      },
      {
        // 布卷管理
        path: 'rolls',
        name: 'Rolls',
        component: Rolls,
        meta: {
          title: '布卷管理',
          icon: 'Box'
        }
      },
      {
        // 实时监控
        path: 'monitor',
        name: 'Monitor',
        component: Monitor,
        meta: {
          title: '实时监控',
          icon: 'VideoCamera'
        }
      },
      {
        // 报告查看
        path: 'reports',
        name: 'Reports',
        component: Reports,
        meta: {
          title: '报告查看',
          icon: 'Document'
        }
      },
      {
        // 系统设置
        path: 'settings',
        name: 'Settings',
        component: Settings,
        meta: {
          title: '系统设置',
          icon: 'Setting'
        }
      }
    ]
  }
]

/**
 * 创建路由器实例
 * 使用HTML5 History模式实现URL路由
 */
const router = createRouter({
  // 使用HTML5 History模式，URL更美观
  history: createWebHistory(),
  // 路由规则
  routes
})

/**
 * 路由守卫 - 每次路由切换前执行的逻辑
 * 可用于权限验证、页面标题设置等
 */
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - FabricEye AI验布系统`
  }
  // 继续导航
  next()
})

// 导出路由实例，供main.js中使用
export default router

/**
 * FabricEye AI验布系统 - 应用入口文件
 * 负责初始化Vue应用、注册插件和全局配置
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

// 创建Vue应用实例
const app = createApp(App)

// 创建Pinia状态管理实例
const pinia = createPinia()

// 注册Element Plus组件库
app.use(ElementPlus)

// 注册Pinia状态管理
app.use(pinia)

// 注册Vue Router路由管理器
app.use(router)

// 注册所有Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 挂载应用到DOM
app.mount('#app')

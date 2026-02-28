import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // Element Plus 自动导入配置
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      // 自动导入的目录
      dirs: ['src/api', 'src/stores', 'src/utils'],
      // 生成自动导入的声明文件
      dts: 'src/auto-imports.d.ts'
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      // 自动导入的目录
      dirs: ['src/components'],
      // 生成组件声明文件
      dts: 'src/components.d.ts'
    })
  ],
  // 路径别名配置
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  // 开发服务器配置
  server: {
    port: 5173,
    proxy: {
      // 代理 /api 请求到后端服务器
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
        // 注意：后端API路径就是 /api/xxx，不需要rewrite
      },
      // 代理 WebSocket 请求到后端服务器
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true
      }
    }
  }
})

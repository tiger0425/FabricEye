<template>
  <!-- 根组件：应用整体布局容器 -->
  <div id="app" class="app-container">
    <!-- 路由视图：显示当前路由对应的页面组件 -->
    <router-view />
  </div>
</template>

<script setup>
/**
 * App.vue - 根组件
 * 这是Vue应用的顶层组件，负责渲染应用的整体结构
 * 所有其他组件都将作为其子组件被路由视图渲染
 */

// 基础布局说明：
// 实际的布局结构（Header + Sidebar + Main Content）在 router/index.js 中的布局组件实现
// 当前组件仅作为路由视图的容器
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  width: 100%;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

#app {
  width: 100%;
  height: 100%;
}

/* 应用容器样式 */
.app-container {
  width: 100%;
  height: 100%;
  background-color: #f5f7fa;
}
</style>

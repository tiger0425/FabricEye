<template>
  <div class="app-layout">
    <!-- 顶部导航栏 -->
    <Header />
    
    <!-- 主体内容区域 -->
    <div class="main-container">
      <!-- 左侧侧边栏 -->
      <Sidebar />
      
      <!-- 右侧主内容区域 -->
      <div class="content-wrapper">
        <!-- 页面内容 -->
        <div class="page-content">
          <router-view />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import Header from './Header.vue'
import Sidebar from './Sidebar.vue'
</script>

<style scoped>
/* 布局容器 */
.app-layout {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 主容器 */
.main-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 内容包装器 */
.content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #f5f7fa;
}

/* 页面内容区域 */
.page-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>

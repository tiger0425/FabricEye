<template>
  <div class="app-sidebar">
    <!-- 侧边栏菜单 -->
    <el-menu
      :default-active="activeMenu"
      class="sidebar-menu"
      :collapse="isCollapse"
      :router="true"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409eff"
    >
      <!-- 首页 -->
      <el-menu-item index="/home">
        <el-icon><HomeFilled /></el-icon>
        <template #title>首页</template>
      </el-menu-item>

      <!-- 布卷管理 -->
      <el-menu-item index="/rolls">
        <el-icon><Box /></el-icon>
        <template #title>布卷管理</template>
      </el-menu-item>

      <!-- 实时监控 -->
      <el-menu-item index="/monitor">
        <el-icon><VideoCamera /></el-icon>
        <template #title>实时监控</template>
      </el-menu-item>

      <!-- 报告查看 -->
      <el-menu-item index="/reports">
        <el-icon><Document /></el-icon>
        <template #title>报告查看</template>
      </el-menu-item>

      <!-- 系统设置 -->
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <template #title>系统设置</template>
      </el-menu-item>
    </el-menu>

    <!-- 折叠按钮 -->
    <div class="collapse-btn" @click="handleCollapse">
      <el-icon>
        <ArrowLeft v-if="!isCollapse" />
        <ArrowRight v-else />
      </el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { 
  HomeFilled, 
  Box, 
  VideoCamera, 
  Document, 
  Setting,
  ArrowLeft,
  ArrowRight
} from '@element-plus/icons-vue'

const route = useRoute()

// 折叠状态
const isCollapse = ref(false)

// 当前激活的菜单
const activeMenu = computed(() => route.path)

/**
 * 处理折叠/展开
 */
function handleCollapse() {
  isCollapse.value = !isCollapse.value
}
</script>

<style scoped>
/* 侧边栏容器 */
.app-sidebar {
  width: 200px;
  height: 100%;
  background-color: #304156;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width 0.3s;
}

/* 菜单容器 */
.sidebar-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}

/* 折叠时的宽度 */
.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
}

/* 菜单项样式 */
.sidebar-menu :deep(.el-menu-item) {
  height: 50px;
  line-height: 50px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background-color: #263445 !important;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background-color: #409eff !important;
}

/* 折叠按钮 */
.collapse-btn {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  padding: 10px;
  cursor: pointer;
  color: #bfcbd9;
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: #409eff;
}
</style>

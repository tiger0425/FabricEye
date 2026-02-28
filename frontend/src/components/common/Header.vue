<template>
  <div class="app-header">
    <!-- 左侧Logo和标题 -->
    <div class="header-left">
      <div class="logo">
        <el-icon :size="24" color="#409eff"><Monitor /></el-icon>
      </div>
      <h1 class="title">FabricEye AI验布系统</h1>
    </div>

    <!-- 右侧操作区域 -->
    <div class="header-right">
      <!-- 消息通知 -->
      <el-badge :value="notificationCount" :hidden="notificationCount === 0" class="notification-badge">
        <el-button :icon="Bell" circle />
      </el-badge>

      <!-- 用户信息 -->
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-info">
          <el-avatar :size="32" :icon="User" />
          <span class="username">管理员</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人中心
            </el-dropdown-item>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              系统设置
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Monitor, 
  Bell, 
  User, 
  ArrowDown, 
  Setting, 
  SwitchButton 
} from '@element-plus/icons-vue'

const router = useRouter()

// 通知数量
const notificationCount = ref(3)

/**
 * 处理用户菜单点击
 */
function handleCommand(command) {
  switch (command) {
    case 'profile':
      // 跳转到个人中心
      console.log('个人中心')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      // 退出登录
      console.log('退出登录')
      break
  }
}
</script>

<style scoped>
/* 头部容器 */
.app-header {
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  z-index: 100;
}

/* 左侧区域 */
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #ecf5ff;
  border-radius: 8px;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

/* 右侧区域 */
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.notification-badge {
  margin-right: 10px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #606266;
}
</style>

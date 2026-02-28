<template>
  <el-card class="status-panel">
    <template #header>
      <div class="panel-header">
        <span>系统状态</span>
        <el-tag :type="systemStatusType" size="small">{{ systemStatusText }}</el-tag>
      </div>
    </template>
    
    <div class="status-content">
      <!-- CPU使用率 -->
      <div class="status-item">
        <div class="status-label">
          <el-icon><Cpu /></el-icon>
          <span>CPU使用率</span>
        </div>
        <el-progress 
          :percentage="cpuUsage" 
          :color="getProgressColor(cpuUsage)"
          :stroke-width="8"
        />
        <span class="status-value">{{ cpuUsage }}%</span>
      </div>
      
      <!-- 内存使用率 -->
      <div class="status-item">
        <div class="status-label">
          <el-icon><Histogram /></el-icon>
          <span>内存使用率</span>
        </div>
        <el-progress 
          :percentage="memoryUsage" 
          :color="getProgressColor(memoryUsage)"
          :stroke-width="8"
        />
        <span class="status-value">{{ memoryUsage }}%</span>
      </div>
      
      <!-- 磁盘使用率 -->
      <div class="status-item">
        <div class="status-label">
          <el-icon><Folder /></el-icon>
          <span>磁盘使用率</span>
        </div>
        <el-progress 
          :percentage="diskUsage" 
          :color="getProgressColor(diskUsage)"
          :stroke-width="8"
        />
        <span class="status-value">{{ diskUsage }}%</span>
      </div>
      
      <!-- 网络状态 -->
      <div class="status-item">
        <div class="status-label">
          <el-icon><Connection /></el-icon>
          <span>网络状态</span>
        </div>
        <el-tag :type="networkStatus === 'online' ? 'success' : 'danger'" size="small">
          {{ networkStatus === 'online' ? '在线' : '离线' }}
        </el-tag>
      </div>
      
      <!-- 验布速度 -->
      <div class="status-item">
        <div class="status-label">
          <el-icon><Timer /></el-icon>
          <span>验布速度</span>
        </div>
        <span class="status-value large">{{ inspectionSpeed }} m/min</span>
      </div>
      
      <!-- 今日验布量 -->
      <div class="status-item">
        <div class="status-label">
          <el-icon><Box /></el-icon>
          <span>今日验布量</span>
        </div>
        <span class="status-value large">{{ todayInspectionCount }} 卷</span>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { 
  Cpu, 
  Histogram,
  Folder, 
  Connection, 
  Timer, 
  Box 
} from '@element-plus/icons-vue'

// 系统状态数据
const cpuUsage = ref(0)
const memoryUsage = ref(0)
const diskUsage = ref(0)
const networkStatus = ref('online')
const inspectionSpeed = ref(0)
const todayInspectionCount = ref(0)

// 定时器
let statusTimer = null

// 系统状态
const systemStatus = computed(() => {
  if (cpuUsage.value > 90 || memoryUsage.value > 90) {
    return 'warning'
  }
  if (networkStatus.value !== 'online') {
    return 'error'
  }
  return 'normal'
})

const systemStatusType = computed(() => {
  const typeMap = {
    normal: 'success',
    warning: 'warning',
    error: 'danger'
  }
  return typeMap[systemStatus.value] || 'info'
})

const systemStatusText = computed(() => {
  const textMap = {
    normal: '正常',
    warning: '警告',
    error: '异常'
  }
  return textMap[systemStatus.value] || '未知'
})

/**
 * 获取进度条颜色
 */
function getProgressColor(percentage) {
  if (percentage < 60) return '#67c23a'
  if (percentage < 85) return '#e6a23c'
  return '#f56c6c'
}

/**
 * 获取系统状态
 */
async function fetchStatus() {
  try {
    // TODO: 调用API获取系统状态
    // 模拟数据
    cpuUsage.value = Math.floor(Math.random() * 60) + 20
    memoryUsage.value = Math.floor(Math.random() * 40) + 30
    diskUsage.value = Math.floor(Math.random() * 30) + 40
    inspectionSpeed.value = Math.floor(Math.random() * 20) + 30
    todayInspectionCount.value = Math.floor(Math.random() * 50) + 10
  } catch (error) {
    console.error('获取系统状态失败:', error)
  }
}

/**
 * 组件挂载时启动定时获取
 */
onMounted(() => {
  fetchStatus()
  statusTimer = setInterval(fetchStatus, 5000)
})

/**
 * 组件卸载时清除定时器
 */
onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})
</script>

<style scoped>
.status-panel {
  margin-top: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-label {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 100px;
  font-size: 14px;
  color: #606266;
}

.status-value {
  font-size: 14px;
  color: #303133;
  min-width: 50px;
  text-align: right;
}

.status-value.large {
  font-size: 18px;
  font-weight: 600;
}

.status-item .el-progress {
  flex: 1;
}
</style>

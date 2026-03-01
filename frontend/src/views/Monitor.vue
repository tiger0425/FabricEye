<template>
  <div class="monitor-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>实时监控</h2>
      <div class="header-actions">
        <el-button 
          :type="monitorStore.isInspecting ? 'danger' : 'success'"
          @click="handleToggleStream"
        >
          <el-icon><VideoCamera /></el-icon>
          {{ monitorStore.isInspecting ? '停止监控' : '开始监控' }}
        </el-button>
      </div>
    </div>

    <!-- 监控内容区域 -->
    <el-row :gutter="20" class="monitor-content">
      <!-- 视频播放区域 -->
      <el-col :span="16">
        <el-card class="video-card">
          <template #header>
            <div class="card-header">
              <span>实时视频</span>
              <div class="stream-status">
                <el-tag :type="getStreamStatusType()">
                  {{ getStreamStatusText() }}
                </el-tag>
              </div>
            </div>
          </template>
          <div class="video-container">
            <VideoPlayer 
              :stream-url="streamUrl"
              :status="monitorStore.streamStatus"
            />
          </div>
          <!-- 帧率显示 -->
          <div class="fps-stats">
            <span>帧率: {{ monitorStore.fpsStats.current }} FPS</span>
            <span>平均: {{ monitorStore.fpsStats.average }} FPS</span>
          </div>
        </el-card>

        <!-- 级联检测状态面板 -->
        <CascadePanel
          :roll-id="currentRollId"
          :ws-message="lastMessage"
          :ws-status="wsStatus"
        />

        <!-- AI状态面板 -->
        <el-card class="status-card">
          <template #header>
            <span>AI分析状态</span>
          </template>
          <div class="ai-status">
            <div class="status-item">
              <span class="label">分析状态:</span>
              <el-tag :type="monitorStore.aiAnalysisStatus.enabled ? 'success' : 'info'">
                {{ monitorStore.aiAnalysisStatus.enabled ? '启用' : '禁用' }}
              </el-tag>
            </div>
            <div class="status-item">
              <span class="label">处理中:</span>
              <el-tag :type="monitorStore.aiAnalysisStatus.processing ? 'warning' : 'success'">
                {{ monitorStore.aiAnalysisStatus.processing ? '处理中' : '空闲' }}
              </el-tag>
            </div>
            <div class="status-item">
              <span class="label">模型状态:</span>
              <el-tag :type="monitorStore.aiAnalysisStatus.modelLoaded ? 'success' : 'warning'">
                {{ monitorStore.aiAnalysisStatus.modelLoaded ? '已加载' : '加载中' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧面板 -->
      <el-col :span="8">
        <!-- 缺陷统计 -->
        <el-card class="stats-card">
          <template #header>
            <span>缺陷统计</span>
          </template>
          <div class="defect-stats">
            <div class="stat-item total">
              <div class="stat-value">{{ monitorStore.defectStats.total }}</div>
              <div class="stat-label">总缺陷数</div>
            </div>
            <div class="stat-item critical">
              <div class="stat-value">{{ monitorStore.defectStats.critical }}</div>
              <div class="stat-label">严重</div>
            </div>
            <div class="stat-item major">
              <div class="stat-value">{{ monitorStore.defectStats.major }}</div>
              <div class="stat-label">主要</div>
            </div>
            <div class="stat-item minor">
              <div class="stat-value">{{ monitorStore.defectStats.minor }}</div>
              <div class="stat-label">次要</div>
            </div>
          </div>
        </el-card>

        <!-- 实时缺陷列表 -->
        <el-card class="defect-card">
          <template #header>
            <div class="card-header">
              <span>实时缺陷</span>
              <el-button text @click="handleClearDefects">清空</el-button>
            </div>
          </template>
          <DefectList 
            :defects="monitorStore.defectList"
            :loading="monitorStore.defectLoading"
            @click="handleDefectClick"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 状态面板 -->
    <StatusPanel />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useMonitorStore } from '@/stores'
import { ElMessage } from 'element-plus'
import VideoPlayer from '@/components/monitor/VideoPlayer.vue'
import DefectList from '@/components/monitor/DefectList.vue'
import StatusPanel from '@/components/monitor/StatusPanel.vue'
import CascadePanel from '@/components/monitor/CascadePanel.vue'
import { useWebSocket } from '@/utils/websocket'

import * as rollsApi from '@/api/rolls'
const monitorStore = useMonitorStore()

// 视频流URL
const streamUrl = ref('')

// 当前布卷 ID（用于级联检测）
const currentRollId = ref(1)

// 定时器
let statsTimer = null

// ==================== WebSocket ====================
// 构建 WebSocket URL，通过 Vite 代理 /ws -> ws://localhost:8000
const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/monitor/${currentRollId.value}`
const { status: wsStatus, lastMessage, connect: wsConnect, disconnect: wsDisconnect } = useWebSocket(wsUrl)

// 监听 WebSocket 消息，处理实时缺陷推送
watch(lastMessage, (msg) => {
  if (!msg) return
  if (msg.type === 'defect_confirmed') {
    monitorStore.addRealTimeDefect(msg)
  }
})


/**
 * 组件挂载时初始化
 */
onMounted(() => {
  initData()
  startStatsPolling()
})

/**
 * 组件卸载时清理
 */
onUnmounted(() => {
  stopStatsPolling()
  stopSnapshotPolling()
})

/**
 * 初始化数据
 */
// Debug: set a global to track
window.initDataCalled = false

async function initData() {
  window.initDataCalled = true
  console.log('initData called, videoList:', monitorStore.videoList.length)
  try {
    // 获取视频流列表
    await monitorStore.fetchVideoList()
    
    // 统一使用快照轮询（模拟实时视频）
    streamUrl.value = '/api/videos/1/snapshot'
    startSnapshotPolling()
    
    // 获取缺陷统计
    await monitorStore.fetchDefectStats()
  } catch (error) {
    console.error('初始化数据失败:', error)
  }
}

/**
 * 启动统计轮询
 */
function startStatsPolling() {
  statsTimer = setInterval(async () => {
    try {
      // 更新缺陷统计
      await monitorStore.fetchDefectStats()
    } catch (error) {
      console.error('更新统计失败:', error)
    }
  }, 5000)
}

/**
 * 停止统计轮询
 */
function stopStatsPolling() {
  if (statsTimer) {
    clearInterval(statsTimer)
    statsTimer = null
  }
}

// 快照轮询定时器
let snapshotTimer = null

// 启动快照轮询（模拟视频）
function startSnapshotPolling() {
  console.log('startSnapshotPolling called!')
  // 每1000ms刷新一次快照，模拟15FPS视频
  snapshotTimer = setInterval(() => {
    // 添加时间戳避免缓存
    streamUrl.value = '/api/videos/1/snapshot?_t=' + Date.now()
  }, 1000)
}

function stopSnapshotPolling() {
  if (snapshotTimer) {
    clearInterval(snapshotTimer)
    snapshotTimer = null
  }
}

/**
 * 切换视频流状态
 */
async function handleToggleStream() {
  try {
    if (monitorStore.streamStatus === 'connected') {
      // 停止验布 - 调用 rolls API
      await rollsApi.stopInspection(currentRollId.value)
      monitorStore.streamStatus = 'disconnected'
      // 断开 WebSocket
      wsDisconnect()
      ElMessage.success('已停止验布')
    } else {
      // 开始验布 - 调用 rolls API
      await rollsApi.startInspection(currentRollId.value)
      monitorStore.streamStatus = 'connected'
      // 连接 WebSocket
      wsConnect()
      ElMessage.success('已开始验布')
    }
  } catch (error) {
    ElMessage.error('操作失败: ' + (error.message || '未知错误'))
  }
}

/**
 * 获取视频流状态类型
 */
function getStreamStatusType() {
  const typeMap = {
    connected: 'success',
    connecting: 'warning',
    disconnected: 'info',
    error: 'danger'
  }
  return typeMap[monitorStore.streamStatus] || 'info'
}

/**
 * 获取视频流状态文本
 */
function getStreamStatusText() {
  const textMap = {
    connected: '已连接',
    connecting: '连接中',
    disconnected: '未连接',
    error: '连接错误'
  }
  return textMap[monitorStore.streamStatus] || '未知'
}

/**
 * 处理缺陷点击
 */
function handleDefectClick(defect) {
  console.log('点击缺陷:', defect)
  // TODO: 跳转到缺陷详情或定位到视频位置
}

/**
 * 清空缺陷列表
 */
function handleClearDefects() {
  monitorStore.clearDefectList()
}
</script>

<style scoped>
.monitor-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.monitor-content {
  margin-bottom: 20px;
}

.video-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-container {
  width: 1000%;
  height: 480px;
  background-color: #000;
  border-radius: 4px;
  overflow: hidden;
}

.fps-stats {
  display: flex;
  gap: 20px;
  margin-top: 10px;
  font-size: 14px;
  color: #909399;
}

.status-card {
  margin-bottom: 20px;
}

.ai-status {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-item .label {
  font-size: 14px;
  color: #606266;
}

.stats-card {
  margin-bottom: 20px;
}

.defect-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  border-radius: 8px;
  background-color: #f5f7fa;
}

.stat-item.total {
  grid-column: span 2;
  background-color: #409eff;
  color: #fff;
}

.stat-item.critical {
  background-color: #f56c6c;
  color: #fff;
}

.stat-item.major {
  background-color: #e6a23c;
  color: #fff;
}

.stat-item.minor {
  background-color: #909399;
  color: #fff;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
}

.stat-label {
  font-size: 12px;
  margin-top: 5px;
}

.defect-card {
  max-height: 400px;
  overflow-y: auto;
}
</style>

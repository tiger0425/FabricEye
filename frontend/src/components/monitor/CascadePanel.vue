<template>
  <el-card class="cascade-panel" shadow="never">
    <!-- 卡片头部：标题 + 运行状态 -->
    <template #header>
      <div class="panel-header">
        <span class="panel-title">级联检测状态</span>
        <div class="panel-status">
          <!-- WebSocket 连接状态 -->
          <span class="ws-indicator" :class="wsStatusClass">
            <span class="ws-dot"></span>
            {{ wsStatusText }}
          </span>
          <!-- 级联运行状态 -->
          <el-tag
            v-if="cascadeStatus"
            :type="cascadeStatus.is_running ? 'success' : 'info'"
            size="small"
            effect="dark"
          >
            {{ cascadeStatus.is_running ? '运行中' : '已停止' }}
          </el-tag>
          <el-tag v-else type="info" size="small" effect="plain">加载中</el-tag>
        </div>
      </div>
    </template>

    <!-- 加载状态 -->
    <div v-if="loading && !cascadeStatus" class="loading-placeholder">
      <el-skeleton :rows="4" animated />
    </div>

    <template v-else>
      <!-- 流水线阶段展示 -->
      <div class="pipeline-section">
        <div class="pipeline-stages">
          <!-- 采集阶段 -->
          <div class="stage-card stage-capture">
            <div class="stage-icon">📷</div>
            <div class="stage-name">采集</div>
            <div class="stage-value">{{ formatNumber(cascadeStatus?.total_frames_captured) }}帧</div>
          </div>

          <div class="stage-arrow">→</div>

          <!-- Flash 检测阶段 -->
          <div class="stage-card stage-flash">
            <div class="stage-icon">⚡</div>
            <div class="stage-name">Flash</div>
            <div class="stage-value">待验: {{ cascadeStatus?.pending_count ?? 0 }}</div>
          </div>

          <div class="stage-arrow">→</div>

          <!-- Plus 确认阶段 -->
          <div class="stage-card stage-plus">
            <div class="stage-icon">🎯</div>
            <div class="stage-name">Plus</div>
            <div class="stage-value">确认: {{ cascadeStatus?.confirmed_count ?? 0 }}</div>
          </div>
        </div>
      </div>

      <!-- 缓冲区与队列进度条 -->
      <div class="buffer-section">
        <div class="buffer-item">
          <div class="buffer-label">
            <span>缓冲区</span>
            <span class="buffer-nums">
              {{ cascadeStatus?.buffer_size ?? 0 }} / {{ cascadeStatus?.buffer_capacity ?? 100 }}
            </span>
          </div>
          <el-progress
            :percentage="bufferPercentage"
            :stroke-width="10"
            :color="bufferColor"
            :show-text="false"
          />
        </div>

        <div class="buffer-item">
          <div class="buffer-label">
            <span>验证队列</span>
            <span class="buffer-nums">
              {{ cascadeStatus?.verification_queue_size ?? 0 }} / 10
            </span>
          </div>
          <el-progress
            :percentage="queuePercentage"
            :stroke-width="10"
            :color="queueColor"
            :show-text="false"
          />
        </div>
      </div>

      <!-- V2.0 级联检测统计 -->
      <div class="stats-section">
        <div class="stats-title">V2.0 级联检测统计</div>
        <div class="stats-grid-v2">
          <!-- 快速通道 -->
          <div class="stat-cell fast-track">
            <span class="stat-icon">⚡</span>
            <span class="stat-label">快速通道确认</span>
            <span class="stat-val">{{ fastTrackCount }}</span>
            <span class="stat-desc">(Flash >= 0.8)</span>
          </div>
          <!-- Plus 复核确认 -->
          <div class="stat-cell plus-confirmed">
            <span class="stat-icon">🎯</span>
            <span class="stat-label">Plus复核确认</span>
            <span class="stat-val">{{ plusConfirmedCount }}</span>
            <span class="stat-desc">(复核通过)</span>
          </div>
          <!-- 待验证队列 -->
          <div class="stat-cell pending-queue">
            <span class="stat-icon">⏳</span>
            <span class="stat-label">待验证队列</span>
            <span class="stat-val">{{ cascadeStatus?.verification_queue_size ?? 0 }}</span>
            <span class="stat-desc">(等待Plus)</span>
          </div>
          <!-- 已拒绝 -->
          <div class="stat-cell rejected">
            <span class="stat-icon">❌</span>
            <span class="stat-label">已拒绝</span>
            <span class="stat-val">{{ cascadeStatus?.rejected_count ?? 0 }}</span>
            <span class="stat-desc">(复核未通过)</span>
          </div>
        </div>
      </div>

      <!-- 验证队列中的缺陷（待复核） -->
      <div v-if="pendingDefects.length > 0" class="pending-section">
        <div class="pending-header">
          <span class="pending-title">🕐 验证队列中的缺陷 ({{ pendingDefects.length }})</span>
          <span class="pending-desc">等待 Plus 引擎复核...</span>
        </div>
        <div class="pending-list">
          <div
            v-for="(defect, index) in pendingDefects"
            :key="'pending-' + index"
            class="pending-item"
          >
            <span class="pending-cid">#{{ defect.cascadeId }}</span>
            <span class="pending-type">{{ defectTypeLabel(defect.defectType) }}</span>
            <span class="pending-confidence">F: {{ formatConfidence(defect.flashConfidence) }}</span>
            <span class="pending-status">等待复核</span>
          </div>
        </div>
      </div>

      <!-- 最新确认缺陷（快速通道 + Plus复核） -->

      <!-- 最新检测缺陷 -->
      <div class="feed-section">
        <div class="feed-title">最新检测</div>
        <div v-if="recentDefects.length === 0" class="feed-empty">
          暂无检测记录
        </div>
        <div v-else class="defect-feed">
          <div
            v-for="(defect, index) in recentDefects"
            :key="(defect.cascadeId || defect.id) + '-' + index"
            class="defect-item"
            :class="'severity-' + (defect.severity || 'minor')"
          >
            <span class="defect-severity-dot" :class="severityDotClass(defect.severity)"></span>
            <span class="defect-route-badge" :class="defect.fastTrack ? 'badge-fast' : 'badge-plus'">
              {{ defect.fastTrack ? '⚡' : '🎯' }}
            </span>
            <span class="defect-type">{{ defectTypeLabel(defect.defectType || defect.defect_type) }}</span>
            <span class="defect-confidence">
              F: {{ formatConfidence(defect.flashConfidence) }}
            </span>
            <span v-if="!defect.fastTrack" class="defect-confidence">
              P: {{ formatConfidence(defect.plusConfidence || defect.confidence) }}
            </span>
            <span class="defect-time">{{ formatRelativeTime(defect.timestamp || defect.detected_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </el-card>
</template>


<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { getCascadeStatus } from '@/api/cascade'
import { useMonitorStore } from '@/stores'

// ==================== Props ====================
const props = defineProps({
  /** 当前布卷 ID */
  rollId: {
    type: Number,
    default: null
  },
  /** 来自父组件的最新 WebSocket 消息 */
  wsMessage: {
    type: Object,
    default: null
  },
  /** WebSocket 连接状态 */
  wsStatus: {
    type: String,
    default: 'disconnected'
  }
})

// ==================== 状态 ====================

// 级联检测状态数据
const cascadeStatus = ref(null)

// 是否正在加载
const loading = ref(false)

// 最近检测到的缺陷（实时 WebSocket 推送）
const recentDefects = ref([])

// 验证队列中的待复核缺陷
const pendingDefects = ref([])

// 轮询定时器
let pollTimer = null

// ==================== 缺陷类型映射 ====================
const DEFECT_TYPE_MAP = {
  hole: '破洞',
  stain: '污渍',
  color_variance: '色差',
  warp_break: '断经',
  weft_break: '断纬'
}

// ==================== Store ====================
const monitorStore = useMonitorStore()

// ==================== 计算属性 ====================

// 快速通道确认的缺陷计数
const fastTrackCount = computed(() => {
  return recentDefects.value.filter(d => d.fastTrack === true).length
})

// Plus复核确认的缺陷计数
const plusConfirmedCount = computed(() => {
  return recentDefects.value.filter(d => d.fastTrack !== true && d.type === 'defect_confirmed').length
})

/** WebSocket 状态样式类 */
const wsStatusClass = computed(() => {
  const map = {
    connecting: 'ws-connecting',
    connected: 'ws-connected',
    disconnected: 'ws-disconnected',
    error: 'ws-error'
  }
  return map[props.wsStatus] || 'ws-disconnected'
})

/** WebSocket 状态文本 */
const wsStatusText = computed(() => {
  const map = {
    connecting: '连接中',
    connected: '实时',
    disconnected: '未连接',
    error: '连接错误'
  }
  return map[props.wsStatus] || '未知'
})

/** 缓冲区占用百分比 */
const bufferPercentage = computed(() => {
  if (!cascadeStatus.value) return 0
  const { buffer_size, buffer_capacity } = cascadeStatus.value
  if (!buffer_capacity || isNaN(buffer_size)) return 0
  return Math.min(Math.max(Math.round((buffer_size / buffer_capacity) * 100), 0), 100)
})

/** 缓冲区颜色（根据占用率变化） */
const bufferColor = computed(() => {
  const pct = bufferPercentage.value
  if (pct >= 90) return '#f56c6c'
  if (pct >= 70) return '#e6a23c'
  return '#67c23a'
})

/** 验证队列百分比（满队列 = 10） */
const queuePercentage = computed(() => {
  if (!cascadeStatus.value || isNaN(cascadeStatus.value.verification_queue_size)) return 0
  return Math.min(Math.max(Math.round((cascadeStatus.value.verification_queue_size / 10) * 100), 0), 100)
})

/** 验证队列颜色 */
const queueColor = computed(() => {
  const pct = queuePercentage.value
  if (pct >= 80) return '#f56c6c'
  if (pct >= 50) return '#e6a23c'
  return '#409eff'
})

// ==================== 工具函数 ====================

/** 格式化大数字（带千分位） */
function formatNumber(num) {
  if (num == null) return '0'
  return Number(num).toLocaleString('zh-CN')
}

/** 格式化置信度为百分比 */
function formatConfidence(val) {
  if (val == null) return 'N/A'
  return (val * 100).toFixed(1) + '%'
}

/** 缺陷类型中文标签 */
function defectTypeLabel(type) {
  return DEFECT_TYPE_MAP[type] || type || '未知'
}

/** 严重程度指示点样式 */
function severityDotClass(severity) {
  const map = {
    severe: 'dot-severe',
    major: 'dot-major',
    minor: 'dot-minor'
  }
  return map[severity] || 'dot-minor'
}

/** 相对时间格式化 */
function formatRelativeTime(timestamp) {
  if (!timestamp) return ''
  
  let date
  if (typeof timestamp === 'number') {
    // 处理秒级时间戳（如果有的话）
    date = new Date(timestamp * 1000)
  } else {
    // 处理日期字符串 (ISO/SQL 格式)
    date = new Date(timestamp)
  }
  
  const now = Date.now()
  const ts = date.getTime()
  
  if (isNaN(ts)) return '未知'
  
  const diff = Math.floor((now - ts) / 1000) // 秒数

  if (diff < 10 && diff > -10) return '刚刚'
  if (diff < 60 && diff >= 0) return `${diff}秒前`
  
  const mins = Math.floor(Math.abs(diff) / 60)
  if (mins < 60) return `${mins}分前`
  
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  
  return `${date.getMonth() + 1}-${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
}

// ==================== 数据获取 ====================

/** 拉取级联检测状态 */
async function fetchStatus() {
  if (!props.rollId) return
  loading.value = true
  try {
    const data = await getCascadeStatus(props.rollId)
    cascadeStatus.value = data
  } catch (error) {
    // 静默处理，避免频繁弹出错误提示
    console.warn('[CascadePanel] 获取级联状态失败:', error)
  } finally {
    loading.value = false
  }
}

/** 启动轮询（2 秒间隔） */
function startPolling() {
  stopPolling()
  fetchStatus()
  pollTimer = setInterval(fetchStatus, 2000)
}

/** 停止轮询 */
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ==================== WebSocket 消息处理 ====================

/** 监听 wsMessage，处理 defect_confirmed 类型消息 */
watch(
  () => props.wsMessage,
  (msg) => {
    if (!msg) return
    if (msg.type === 'defect_confirmed') {
      // 确认的缺陷（快速通道或Plus复核）
      recentDefects.value.unshift(msg)
      if (recentDefects.value.length > 20) {
        recentDefects.value.pop()
      }
      // 如果是快速通道，从待验证列表中移除
      if (msg.fastTrack) {
        const idx = pendingDefects.value.findIndex(d => d.cascadeId === msg.cascadeId)
        if (idx > -1) pendingDefects.value.splice(idx, 1)
      }
    } else if (msg.type === 'defect_pending') {
      // 新检测进入验证队列
      pendingDefects.value.unshift({
        cascadeId: msg.cascadeId,
        defectType: msg.defectType,
        flashConfidence: msg.flashConfidence,
        timestamp: msg.timestamp
      })
      if (pendingDefects.value.length > 10) {
        pendingDefects.value.pop()
      }
    }
  }
)


/** 监听 rollId 变化 */
watch(
  () => props.rollId,
  (newId) => {
    if (newId) {
      cascadeStatus.value = null
      // 这里的清空改为从全局 Store 获取最近的数据
      // 避免"最新检测"在初始化时显示为空
      recentDefects.value = []
      startPolling()
    } else {
      stopPolling()
    }
  }
)

/** 监听全局 Store 的缺陷列表，同步到"最新检测" */
watch(
  () => monitorStore.defectList,
  (newList) => {
    if (newList && newList.length > 0 && recentDefects.value.length === 0) {
      // 页面初次加载时，同步最近的 5 条数据到面板
      recentDefects.value = newList.slice(0, 5)
    }
  },
  { immediate: true }
)

// ==================== 生命周期 ====================

onMounted(() => {
  if (props.rollId) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
/* ========== 卡片容器 ========== */
.cascade-panel {
  margin-bottom: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

/* ========== 头部 ========== */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  letter-spacing: 0.5px;
}

.panel-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* WebSocket 状态指示器 */
.ws-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.ws-connected .ws-dot {
  background-color: #67c23a;
  box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.3);
  animation: pulse-green 1.5s infinite;
}

.ws-connecting .ws-dot {
  background-color: #e6a23c;
  animation: pulse-yellow 1s infinite;
}

.ws-disconnected .ws-dot {
  background-color: #909399;
}

.ws-error .ws-dot {
  background-color: #f56c6c;
}

.ws-connected {
  color: #67c23a;
}

.ws-connecting {
  color: #e6a23c;
}

.ws-disconnected {
  color: #909399;
}

.ws-error {
  color: #f56c6c;
}

@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.3); }
  50% { box-shadow: 0 0 0 5px rgba(103, 194, 58, 0.1); }
}

@keyframes pulse-yellow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ========== 加载骨架 ========== */
.loading-placeholder {
  padding: 10px 0;
}

/* ========== 流水线阶段 ========== */
.pipeline-section {
  margin-bottom: 18px;
}

.pipeline-stages {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stage-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  text-align: center;
  transition: transform 0.2s ease;
}

.stage-card:hover {
  transform: translateY(-2px);
}

.stage-capture {
  background: linear-gradient(135deg, #e8f4fd 0%, #d4eaf7 100%);
  border: 1px solid #bdd7ee;
}

.stage-flash {
  background: linear-gradient(135deg, #fef9e8 0%, #fdf0c6 100%);
  border: 1px solid #f5d97a;
}

.stage-plus {
  background: linear-gradient(135deg, #edf7ee 0%, #d7f0d9 100%);
  border: 1px solid #aad6ae;
}

.stage-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.stage-name {
  font-size: 11px;
  color: #606266;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.stage-value {
  font-size: 12px;
  color: #303133;
  font-weight: 500;
}

.stage-arrow {
  color: #c0c4cc;
  font-size: 16px;
  flex-shrink: 0;
}

/* ========== 缓冲区进度条 ========== */
.buffer-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 18px;
}

.buffer-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.buffer-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #606266;
}

.buffer-nums {
  font-size: 11px;
  color: #909399;
  font-variant-numeric: tabular-nums;
}

/* ========== 统计区域 ========== */
.stats-section {
  margin-bottom: 18px;
}

.stats-title,
.feed-title {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f2f5;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.stat-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 6px;
  background-color: #f5f7fa;
}

.stat-cell.confirmed {
  background-color: #f0f9eb;
}

.stat-cell.rejected {
  background-color: #fef0f0;
}

.stat-cell.pending {
  background-color: #fdf6ec;
}

.stat-cell.expired {
  background-color: #f4f4f5;
}

.stat-icon {
  font-size: 14px;
}

.stat-label {
  font-size: 12px;
  color: #606266;
  flex: 1;
}

.stat-val {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
  font-variant-numeric: tabular-nums;
}

/* ========== 实时缺陷动态 ========== */
.feed-section {
  /* no extra margin needed at bottom */
}

.feed-empty {
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
  padding: 20px 0;
}

.defect-feed {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.defect-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  background-color: #fafafa;
  border: 1px solid #f0f2f5;
  transition: background-color 0.2s ease;
  animation: slide-in 0.3s ease;
}

.defect-item:hover {
  background-color: #f0f2f5;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 严重程度指示点 */
.defect-severity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-severe {
  background-color: #f56c6c;
}

.dot-major {
  background-color: #e6a23c;
}

.dot-minor {
  background-color: #909399;
}

.defect-type {
  font-weight: 600;
  color: #303133;
  min-width: 32px;
}

.defect-confidence {
  color: #606266;
  font-variant-numeric: tabular-nums;
}

.defect-time {
  margin-left: auto;
  color: #c0c4cc;
  white-space: nowrap;
  font-size: 11px;
}

.defect-route-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  font-size: 12px;
  margin-right: 4px;
}

.badge-fast {
  background-color: #67c23a;
  color: white;
}

.badge-plus {
  background-color: #409eff;
  color: white;
}

/* ========== V2.0 统计网格 ========== */
.stats-grid-v2 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 10px;
}

.stats-grid-v2 .stat-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px;
  background-color: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.stats-grid-v2 .stat-cell .stat-icon {
  font-size: 18px;
  margin-bottom: 4px;
}

.stats-grid-v2 .stat-cell .stat-label {
  font-size: 12px;
  color: #606266;
  margin-bottom: 2px;
  flex: none;
}

.stats-grid-v2 .stat-cell .stat-val {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.stats-grid-v2 .stat-cell .stat-desc {
  font-size: 10px;
  color: #909399;
  margin-top: 2px;
}

.stats-grid-v2 .stat-cell.fast-track {
  background-color: #f0f9eb;
  border-color: #67c23a;
}

.stats-grid-v2 .stat-cell.fast-track .stat-val {
  color: #67c23a;
}

.stats-grid-v2 .stat-cell.plus-confirmed {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.stats-grid-v2 .stat-cell.plus-confirmed .stat-val {
  color: #409eff;
}

.stats-grid-v2 .stat-cell.pending-queue {
  background-color: #fdf6ec;
  border-color: #e6a23c;
}

.stats-grid-v2 .stat-cell.pending-queue .stat-val {
  color: #e6a23c;
}

.stats-grid-v2 .stat-cell.rejected {
  background-color: #fef0f0;
  border-color: #f56c6c;
}

.stats-grid-v2 .stat-cell.rejected .stat-val {
  color: #f56c6c;
}

/* ========== 待验证区域 ========== */
.pending-section {
  margin-top: 16px;
  padding: 12px;
  background-color: #fdf6ec;
  border: 1px solid #e6a23c;
  border-radius: 6px;
}

.pending-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.pending-title {
  font-weight: 600;
  color: #e6a23c;
}

.pending-desc {
  font-size: 12px;
  color: #909399;
}

.pending-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pending-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background-color: white;
  border-radius: 4px;
  font-size: 13px;
}

.pending-cid {
  color: #909399;
  font-size: 11px;
  margin-right: 8px;
  min-width: 30px;
}

.pending-type {
  font-weight: 500;
  color: #303133;
  min-width: 40px;
  margin-right: 8px;
}

.pending-confidence {
  color: #606266;
  font-size: 12px;
  margin-right: 8px;
}

.pending-status {
  margin-left: auto;
  font-size: 11px;
  color: #e6a23c;
  background-color: #fdf6ec;
  padding: 2px 6px;
  border-radius: 3px;
}
</style>

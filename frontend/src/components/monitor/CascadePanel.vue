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

      <!-- 统计数据 -->
      <div class="stats-section">
        <div class="stats-title">统计</div>
        <div class="stats-grid">
          <div class="stat-cell confirmed">
            <span class="stat-icon">✅</span>
            <span class="stat-label">已确认</span>
            <span class="stat-val">{{ cascadeStatus?.confirmed_count ?? 0 }}</span>
          </div>
          <div class="stat-cell rejected">
            <span class="stat-icon">❌</span>
            <span class="stat-label">已拒绝</span>
            <span class="stat-val">{{ cascadeStatus?.rejected_count ?? 0 }}</span>
          </div>
          <div class="stat-cell pending">
            <span class="stat-icon">⏳</span>
            <span class="stat-label">待验证</span>
            <span class="stat-val">{{ cascadeStatus?.pending_count ?? 0 }}</span>
          </div>
          <div class="stat-cell expired">
            <span class="stat-icon">💨</span>
            <span class="stat-label">已过期</span>
            <span class="stat-val">{{ cascadeStatus?.expired_count ?? 0 }}</span>
          </div>
        </div>
      </div>

      <!-- 最新检测缺陷 -->
      <div class="feed-section">
        <div class="feed-title">最新检测</div>
        <div v-if="recentDefects.length === 0" class="feed-empty">
          暂无检测记录
        </div>
        <div v-else class="defect-feed">
          <div
            v-for="(defect, index) in recentDefects"
            :key="defect.cascadeId + '-' + index"
            class="defect-item"
            :class="'severity-' + defect.severity"
          >
            <span class="defect-severity-dot" :class="severityDotClass(defect.severity)"></span>
            <span class="defect-type">{{ defectTypeLabel(defect.defectType) }}</span>
            <span class="defect-confidence">
              Flash: {{ formatConfidence(defect.flashConfidence) }}
            </span>
            <span class="defect-confidence">
              Plus: {{ formatConfidence(defect.plusConfidence) }}
            </span>
            <span class="defect-time">{{ formatRelativeTime(defect.timestamp) }}</span>
          </div>
        </div>
      </div>
    </template>
  </el-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { getCascadeStatus } from '@/api/cascade'

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

// ==================== 计算属性 ====================

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
  const now = Date.now()
  const ts = new Date(timestamp).getTime()
  const diff = Math.floor((now - ts) / 1000) // 秒数

  if (diff < 10) return '刚刚'
  if (diff < 60) return `${diff}秒前`
  const mins = Math.floor(diff / 60)
  if (mins < 60) return `${mins}分前`
  const hours = Math.floor(mins / 60)
  return `${hours}小时前`
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
      // 将新缺陷插入顶部，最多保留 20 条
      recentDefects.value.unshift(msg)
      if (recentDefects.value.length > 20) {
        recentDefects.value.pop()
      }
    }
  }
)

/** 监听 rollId 变化，重启轮询 */
watch(
  () => props.rollId,
  (newId) => {
    if (newId) {
      cascadeStatus.value = null
      recentDefects.value = []
      startPolling()
    } else {
      stopPolling()
    }
  }
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
</style>

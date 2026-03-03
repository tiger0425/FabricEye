<template>
  <div class="video-playback">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2>视频回放</h2>
        <span v-if="videosStore.currentVideo" class="video-meta">
          布卷号: {{ videosStore.currentVideo.roll_id }}
        </span>
      </div>
      <el-button @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <el-card class="video-card" v-loading="videosStore.loading">
      <!-- 视频播放器区域 -->
      <div class="player-container">
        <div class="video-wrapper">
          <video
            ref="videoRef"
            class="video-element"
            :src="videosStore.videoUrl"
            controls
            @timeupdate="onTimeUpdate"
            @loadedmetadata="onLoadedMetadata"
            @play="isPlaying = true"
            @pause="isPlaying = false"
          ></video>
          
          <!-- SVG 缺陷标记层 -->
          <svg
            v-if="videosStore.currentDefects.length > 0"
            class="defect-overlay"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            <g
              v-for="defect in videosStore.currentDefects"
              :key="defect.id"
              class="defect-marker"
              @click="showDefectDetail(defect)"
            >
              <rect
                :x="getBboxX(defect.bbox)"
                :y="getBboxY(defect.bbox)"
                :width="getBboxWidth(defect.bbox)"
                :height="getBboxHeight(defect.bbox)"
                :stroke="getSeverityColor(defect.severity)"
                stroke-width="0.5"
                fill="rgba(255,255,255,0.1)"
                rx="0.5"
              />
              <text
                :x="getBboxX(defect.bbox)"
                :y="getBboxY(defect.bbox) - 1"
                :fill="getSeverityColor(defect.severity)"
                font-size="3"
                font-weight="bold"
              >{{ defect.typeCn }}</text>
            </g>
          </svg>
        </div>

        <!-- 播放控制和时间显示 -->
        <div class="playback-controls">
          <div class="time-display">
            <span>{{ formatTime(videosStore.currentTime) }}</span>
            <span class="time-separator">/</span>
            <span>{{ formatTime(videosStore.duration) }}</span>
          </div>
          <div class="control-buttons">
            <el-button
              type="primary"
              :disabled="!videosStore.currentVideo"
              @click="generateMarkedVideo"
              :loading="generatingMarked"
            >
              <el-icon><VideoCamera /></el-icon>
              生成标记视频
            </el-button>
          </div>
        </div>
      </div>

      <!-- 缺陷时间轴 -->
      <div class="timeline-section" v-if="videosStore.defectTimeline.length > 0">
        <h4>缺陷时间轴</h4>
        <div class="timeline-container">
          <el-slider
            v-model="sliderValue"
            :max="videosStore.duration || 100"
            :step="0.1"
            show-stops
            :marks="defectMarks"
            @change="onTimelineChange"
          />
          <div class="timeline-legend">
            <span
              v-for="type in uniqueDefectTypes"
              :key="type.type"
              class="legend-item"
            >
              <span
                class="legend-dot"
                :style="{ backgroundColor: getSeverityColor(type.severity) }"
              ></span>
              {{ type.typeCn }}
            </span>
          </div>
        </div>
      </div>

      <!-- 缺陷列表 -->
      <div class="defect-list-section" v-if="videosStore.defects.length > 0">
        <h4>缺陷列表 (共 {{ videosStore.defects.length }} 个)</h4>
        <el-table :data="videosStore.defects" style="width: 100%" max-height="300">
          <el-table-column prop="timestamp" label="时间" width="100">
            <template #default="{ row }">
              {{ formatTime(row.timestamp) }}
            </template>
          </el-table-column>
          <el-table-column prop="typeCn" label="类型" width="100" />
          <el-table-column prop="severity" label="严重程度" width="100">
            <template #default="{ row }">
              <el-tag :type="getSeverityTagType(row.severity)" size="small">
                {{ getSeverityText(row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度" width="100">
            <template #default="{ row }">
              {{ (row.confidence * 100).toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column label="位置" width="150">
            <template #default="{ row }">
              {{ row.position || '(未知)' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="jumpToDefect(row)">
                跳转
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-if="!videosStore.loading && !videosStore.currentVideo"
        description="视频加载失败"
      />
    </el-card>

    <!-- 缺陷详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="缺陷详情"
      width="400px"
    >
      <el-descriptions :column="1" border v-if="selectedDefect">
        <el-descriptions-item label="缺陷类型">
          {{ selectedDefect.typeCn }}
        </el-descriptions-item>
        <el-descriptions-item label="严重程度">
          <el-tag :type="getSeverityTagType(selectedDefect.severity)">
            {{ getSeverityText(selectedDefect.severity) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="置信度">
          {{ (selectedDefect.confidence * 100).toFixed(1) }}%
        </el-descriptions-item>
        <el-descriptions-item label="时间戳">
          {{ formatTime(selectedDefect.timestamp) }}
        </el-descriptions-item>
        <el-descriptions-item label="位置坐标">
          ({{ Math.round(selectedDefect.bbox?.[0] || 0) }},
           {{ Math.round(selectedDefect.bbox?.[1] || 0) }}) -
          ({{ Math.round(selectedDefect.bbox?.[2] || 0) }},
           {{ Math.round(selectedDefect.bbox?.[3] || 0) }})
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, VideoCamera } from '@element-plus/icons-vue'
import { useVideosStore } from '@/stores'
import { generateMarkedVideo as generateMarkedVideoApi } from '@/api/videos'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const videosStore = useVideosStore()

const videoId = computed(() => route.query.videoId || route.params.videoId)
const videoRef = ref(null)
const isPlaying = ref(false)
const sliderValue = ref(0)
const detailDialogVisible = ref(false)
const selectedDefect = ref(null)
const generatingMarked = ref(false)

// 监听 store 时间变化，同步到 slider
watch(() => videosStore.currentTime, (time) => {
  sliderValue.value = time
})

// 计算缺陷标记（用于时间轴）
const defectMarks = computed(() => {
  const marks = {}
  videosStore.defectTimeline.forEach(defect => {
    marks[defect.timestamp] = ''
  })
  return marks
})

// 获取唯一的缺陷类型（用于图例）
const uniqueDefectTypes = computed(() => {
  const types = {}
  videosStore.defects.forEach(d => {
    if (!types[d.type]) {
      types[d.type] = { type: d.type, typeCn: d.typeCn, severity: d.severity }
    }
  })
  return Object.values(types)
})

// 加载视频数据
onMounted(async () => {
  if (videoId.value) {
    try {
      await videosStore.loadVideoDetail(videoId.value)
      await videosStore.loadVideoDefects(videoId.value)
    } catch (error) {
      ElMessage.error('加载视频数据失败')
    }
  }
})

// 清理
onUnmounted(() => {
  videosStore.clearVideo()
})

// 视频时间更新
function onTimeUpdate(e) {
  videosStore.setCurrentTime(e.target.currentTime)
}

// 视频元数据加载完成
function onLoadedMetadata(e) {
  videosStore.setDuration(e.target.duration)
}

// 时间轴跳转
function onTimelineChange(value) {
  if (videoRef.value) {
    videoRef.value.currentTime = value
  }
}

// 跳转到指定缺陷
function jumpToDefect(defect) {
  if (videoRef.value && defect.timestamp !== undefined) {
    videoRef.value.currentTime = defect.timestamp
    videoRef.value.play()
  }
}

// 显示缺陷详情
function showDefectDetail(defect) {
  selectedDefect.value = defect
  detailDialogVisible.value = true
}

// 生成标记视频
async function generateMarkedVideo() {
  if (!videoId.value) return
  
  generatingMarked.value = true
  try {
    await generateMarkedVideoApi(videoId.value)
    ElMessage.success('标记视频生成任务已提交')
  } catch (error) {
    ElMessage.error('生成标记视频失败')
  } finally {
    generatingMarked.value = false
  }
}

// 格式化时间
function formatTime(seconds) {
  if (seconds === undefined || seconds === null) return '00:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 获取严重程度颜色
function getSeverityColor(severity) {
  const colors = {
    minor: '#f4a460',      // 黄色
    moderate: '#ff8c00',   // 橙色
    severe: '#ff4500'      // 红色
  }
  return colors[severity] || '#909399'
}

// 获取严重程度标签类型
function getSeverityTagType(severity) {
  const types = {
    minor: 'warning',
    moderate: 'danger',
    severe: 'danger'
  }
  return types[severity] || 'info'
}

// 获取严重程度文本
function getSeverityText(severity) {
  const texts = {
    minor: '轻微',
    moderate: '中等',
    severe: '严重'
  }
  return texts[severity] || '未知'
}

// 边界框坐标转换（假设视频显示区域为 100x100）
// 边界框坐标转换（bbox为数组格式 [x1, y1, x2, y2]）
function getBboxX(bbox) {
  if (!bbox || !Array.isArray(bbox)) return 0
  // 假设原始坐标是相对于视频分辨率的，需要归一化到 0-100
  return (bbox[0] / 640) * 100 || 0
}

function getBboxY(bbox) {
  if (!bbox || !Array.isArray(bbox)) return 0
  return (bbox[1] / 480) * 100 || 0
}

function getBboxWidth(bbox) {
  if (!bbox || !Array.isArray(bbox)) return 0
  return ((bbox[2] - bbox[0]) / 640) * 100 || 0
}

function getBboxHeight(bbox) {
  if (!bbox || !Array.isArray(bbox)) return 0
  return ((bbox[3] - bbox[1]) / 480) * 100 || 0
}
</script>

<style scoped>
.video-playback {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.video-meta {
  color: #909399;
  font-size: 14px;
}

.video-card {
  min-height: 500px;
}

.player-container {
  margin-bottom: 20px;
}

.video-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background-color: #000;
  border-radius: 4px;
  overflow: hidden;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.defect-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.defect-marker {
  pointer-events: auto;
  cursor: pointer;
}

.defect-marker:hover rect {
  fill: rgba(255, 255, 255, 0.3);
  stroke-width: 0.8;
}

.playback-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.time-display {
  font-size: 14px;
  color: #606266;
}

.time-separator {
  margin: 0 4px;
  color: #909399;
}

.timeline-section {
  margin-top: 24px;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.timeline-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #303133;
}

.timeline-container {
  padding: 0 12px;
}

.timeline-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.defect-list-section {
  margin-top: 24px;
}

.defect-list-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #303133;
}
</style>

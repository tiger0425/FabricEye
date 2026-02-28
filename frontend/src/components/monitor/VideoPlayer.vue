<template>
  <div class="video-player">
    <!-- 视频容器 -->
    <div class="video-container" @click="handleVideoClick">
      <!-- 加载状态 -->
      <div v-if="status === 'connecting'" class="loading-overlay">
        <el-icon class="loading-icon" :size="48"><Loading /></el-icon>
        <p>正在连接视频流...</p>
      </div>
      
      <!-- 错误状态 -->
      <div v-else-if="status === 'error'" class="error-overlay">
        <el-icon :size="48"><Warning /></el-icon>
        <p>视频流连接失败</p>
        <el-button size="small" @click="handleRetry">重试</el-button>
      </div>
      
      <!-- MJPEG流使用img标签 -->
      <img
        v-if="isMjpegStream && streamUrl"
        ref="imgRef"
        class="video-element mjpeg"
        :src="streamUrl"
        @load="onMjpegLoad"
        @error="onMjpegError"
      />
      
      <!-- 视频元素 -->
      <video
        v-else-if="!isMjpegStream"
        ref="videoRef"
        class="video-element"
        autoplay
        muted
        playsinline
      />
      
      <!-- 全屏按钮 -->
      <div class="fullscreen-btn" @click="handleFullscreen">
        <el-icon><FullScreen /></el-icon>
      </div>
    </div>
    
    <!-- 视频控制条 -->
    <div class="video-controls">
      <el-button 
        :icon="isPlaying ? VideoPause : VideoPlay" 
        circle 
        size="small"
        @click="togglePlay"
      />
      <div class="time-display">
        {{ currentTime }} / {{ duration }}
      </div>
      <el-slider 
        v-model="progress" 
        :show-tooltip="false"
        @change="handleSeek"
      />
      <el-button :icon="Mute" circle size="small" @click="toggleMute" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { 
  Loading, 
  Warning, 
  FullScreen, 
  VideoPause, 
  VideoPlay,
  Mute,
  Microphone 
} from '@element-plus/icons-vue'

// 定义Props
const props = defineProps({
  // 视频流URL
  streamUrl: {
    type: String,
    default: ''
  },
  // 连接状态
  status: {
    type: String,
    default: 'disconnected' // disconnected, connecting, connected, error
  }
})

// 定义Emits
const emit = defineEmits(['play', 'pause', 'error'])

// 视频引用
const videoRef = ref(null)
const imgRef = ref(null)

// 检测是否为MJPEG流
const isMjpegStream = computed(() => {
  console.log('isMjpegStream computed, streamUrl:', props.streamUrl, 'result:', props.streamUrl && (props.streamUrl.includes('/stream') || props.streamUrl.includes('/snapshot')))
  return props.streamUrl && (props.streamUrl.includes('/stream') || props.streamUrl.includes('/snapshot'))
})


const isPlaying = ref(false)

// 进度
const progress = ref(0)

// 静音状态
const isMuted = ref(false)

// 当前时间
const currentTime = ref('00:00:00')

// 总时长
const duration = ref('00:00:00')

/**
 * 监听streamUrl变化
 */
watch(() => props.streamUrl, (newUrl) => {
  if (newUrl && props.status === 'connected') {
    loadStream(newUrl)
  }
})

/**
 * 监听status变化
 */
watch(() => props.status, (newStatus) => {
  if (newStatus === 'connected' && props.streamUrl) {
    loadStream(props.streamUrl)
  }
})

/**
 * 加载视频流
 */
function loadStream(url) {
  if (!url) return
  
  // MJPEG流使用img标签处理
  if (isMjpegStream.value) {
    // img标签会自动加载，不需要额外处理
    isPlaying.value = true
    return
  }
  
  // 传统视频流
  if (!videoRef.value) return
  try {
    videoRef.value.src = url
    videoRef.value.play()
    isPlaying.value = true
  } catch (error) {
    console.error('加载视频流失败:', error)
    emit('error', error)
  }
}

function onMjpegLoad() {
  isPlaying.value = true
}

function onMjpegError() {
  emit('error', new Error('MJPEG流加载失败'))
}

/**
 * 视频点击
 */
function handleVideoClick() {
  if (isPlaying.value) {
    videoRef.value?.pause()
    isPlaying.value = false
  } else {
    videoRef.value?.play()
    isPlaying.value = true
  }
}

/**
 * 切换播放/暂停
 */
function togglePlay() {
  if (isPlaying.value) {
    videoRef.value?.pause()
    isPlaying.value = false
    emit('pause')
  } else {
    videoRef.value?.play()
    isPlaying.value = true
    emit('play')
  }
}

/**
 * 跳转播放进度
 */
function handleSeek(value) {
  if (videoRef.value) {
    videoRef.value.currentTime = (value / 100) * videoRef.value.duration
  }
}

/**
 * 切换静音
 */
function toggleMute() {
  if (videoRef.value) {
    videoRef.value.muted = !videoRef.value.muted
    isMuted.value = videoRef.value.muted
  }
}

/**
 * 全屏
 */
function handleFullscreen() {
  const container = videoRef.value?.parentElement
  if (container) {
    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      container.requestFullscreen()
    }
  }
}

/**
 * 重试
 */
function handleRetry() {
  if (props.streamUrl) {
    loadStream(props.streamUrl)
  }
}

// 定时器
let timeUpdateTimer = null

/**
 * 组件挂载
 */
onMounted(() => {
  // 定时更新播放进度
  timeUpdateTimer = setInterval(() => {
    if (videoRef.value) {
      const current = videoRef.value.currentTime
      const total = videoRef.value.duration || 0
      
      progress.value = total > 0 ? (current / total) * 100 : 0
      currentTime.value = formatTime(current)
      duration.value = formatTime(total)
    }
  }, 1000)
})

/**
 * 组件卸载
 */
onUnmounted(() => {
  if (timeUpdateTimer) {
    clearInterval(timeUpdateTimer)
  }
  // 停止视频
  if (videoRef.value) {
    videoRef.value.pause()
    videoRef.value.src = ''
  }
})

/**
 * 格式化时间
 */
function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '00:00:00'
  
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  
  return [h, m, s].map(v => v.toString().padStart(2, '0')).join(':')
}
</script>

<style scoped>
.video-player {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.video-container {
  flex: 1;
  position: relative;
  background-color: #000;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* 加载遮罩 */
.loading-overlay,
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.7);
  color: #fff;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-overlay p,
.error-overlay p {
  margin-top: 15px;
  font-size: 14px;
}

/* 全屏按钮 */
.fullscreen-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.5);
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.3s;
}

.video-container:hover .fullscreen-btn {
  opacity: 1;
}

/* 控制条 */
.video-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background-color: #1a1a1a;
}

.time-display {
  color: #fff;
  font-size: 12px;
  min-width: 80px;
  text-align: center;
}

.video-controls .el-slider {
  flex: 1;
}
</style>

/**
 * 视频播放状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as videosApi from '@/api/videos'

export const useVideosStore = defineStore('videos', () => {
  // ==================== 状态定义 ====================
  
  // 当前播放的视频信息
  const currentVideo = ref(null)
  
  // 视频播放URL
  const videoUrl = ref('')
  
  // 视频关联的缺陷列表
  const defects = ref([])
  
  // 加载状态
  const loading = ref(false)
  
  // 当前播放时间（秒）
  const currentTime = ref(0)
  
  // 视频总时长（秒）
  const duration = ref(0)
  
  // ==================== 计算属性 ====================
  
  // 当前时间附近的缺陷（前后2秒）
  const currentDefects = computed(() => {
    const window = 2
    return defects.value.filter(d => {
      const t = d.timestamp || 0
      return Math.abs(t - currentTime.value) <= window
    })
  })
  
  // 缺陷时间轴数据（用于时间轴组件）
  const defectTimeline = computed(() => {
    return defects.value.map(d => ({
      id: d.id,
      timestamp: d.timestamp || 0,
      type: d.type,
      typeCn: d.typeCn,
      severity: d.severity
    })).sort((a, b) => a.timestamp - b.timestamp)
  })
  
  // ==================== Actions ====================
  
  /**
   * 加载视频详情
   * @param {string} videoId - 视频ID
   */
  async function loadVideoDetail(videoId) {
    loading.value = true
    try {
      const result = await videosApi.getVideoDetail(videoId)
      const data = result.data || result
      currentVideo.value = data
      videoUrl.value = videosApi.getVideoPlayUrl(videoId)
      return data
    } catch (error) {
      console.error('加载视频详情失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 加载视频缺陷列表
   * @param {string} videoId - 视频ID
   */
  async function loadVideoDefects(videoId) {
    try {
      const result = await videosApi.getVideoDefects(videoId)
      const data = result.data || result
      // 兼容后端返回的不同结构：纯数组、{list: []} 或 {defects: []}
      if (Array.isArray(data)) {
        defects.value = data
      } else if (data.defects && Array.isArray(data.defects)) {
        defects.value = data.defects
      } else if (data.list && Array.isArray(data.list)) {
        defects.value = data.list
      } else {
        defects.value = []
      }
      return defects.value
    } catch (error) {
      console.error('加载视频缺陷失败:', error)
      throw error
    }
  }
  
  /**
   * 更新当前播放时间
   * @param {number} time - 时间（秒）
   */
  function setCurrentTime(time) {
    currentTime.value = time
  }
  
  /**
   * 更新视频总时长
   * @param {number} d - 时长（秒）
   */
  function setDuration(d) {
    duration.value = d
  }
  
  /**
   * 跳转到指定时间
   * @param {number} timestamp - 目标时间（秒）
   */
  function seekTo(timestamp) {
    currentTime.value = timestamp
    return timestamp
  }
  
  /**
   * 清空当前视频
   */
  function clearVideo() {
    currentVideo.value = null
    videoUrl.value = ''
    defects.value = []
    currentTime.value = 0
    duration.value = 0
  }
  
  // 导出状态和方法
  return {
    currentVideo,
    videoUrl,
    defects,
    loading,
    currentTime,
    duration,
    currentDefects,
    defectTimeline,
    loadVideoDetail,
    loadVideoDefects,
    setCurrentTime,
    setDuration,
    seekTo,
    clearVideo
  }
})

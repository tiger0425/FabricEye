/**
 * 实时监控状态管理
 * 管理视频流、缺陷检测和监控相关状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as videosApi from '@/api/videos'
import * as defectsApi from '@/api/defects'

/**
 * 实时监控Store
 * 使用Composition API风格定义
 */
export const useMonitorStore = defineStore('monitor', () => {
  // ==================== 视频流状态 ====================
  
  // 视频流列表
  const videoList = ref([])
  
  // 当前选中的视频流
  const currentVideo = ref(null)
  
  // 视频流连接状态
  const streamStatus = ref('disconnected') // disconnected, connecting, connected, error
  
  // 视频流加载状态
  const videoLoading = ref(false)

  // ==================== 缺陷检测状态 ====================
  
  // 实时缺陷列表
  const defectList = ref([])
  
  // 缺陷统计
  const defectStats = ref({
    total: 0,
    critical: 0,
    major: 0,
    minor: 0
  })
  
  // 缺陷分类统计
  const defectCategories = ref([])
  
  // 缺陷加载状态
  const defectLoading = ref(false)

  // ==================== 系统状态 ====================
  
  // AI分析状态
  const aiAnalysisStatus = ref({
    enabled: true,
    processing: false,
    modelLoaded: false
  })
  
  // 帧率统计
  const fpsStats = ref({
    current: 0,
    average: 0,
    min: 0,
    max: 0
  })

  // ==================== 计算属性 ====================
  
  // 是否正在验布
  const isInspecting = computed(() => streamStatus.value === 'connected')
  
  // 是否有实时缺陷
  const hasDefects = computed(() => defectList.value.length > 0)
  
  // 严重缺陷数量
  const criticalDefects = computed(() => 
    defectList.value.filter(d => d.severity === 'critical').length
  )

  // ==================== Actions ====================
  
  /**
   * 获取视频流列表
   */
  async function fetchVideoList() {
    videoLoading.value = true
    try {
      const data = await videosApi.getRollVideos()
      videoList.value = data || []
    } catch (error) {
      console.error('获取视频流列表失败:', error)
      throw error
    } finally {
      videoLoading.value = false
    }
  }
  
  /**
   * 获取视频流详情
   * @param {string} id - 视频流ID
   */
  async function fetchVideoDetail(id) {
    videoLoading.value = true
    try {
      const data = await videosApi.getVideoDetail(id)
      currentVideo.value = data
      return data
    } catch (error) {
      console.error('获取视频流详情失败:', error)
      throw error
    } finally {
      videoLoading.value = false
    }
  }
  
  /**
   * 启动视频流
   * @param {string} id - 视频流ID
   */
  async function startStream(id) {
    streamStatus.value = 'connecting'
    try {
      await videosApi.startVideoStream(id)
      streamStatus.value = 'connected'
    } catch (error) {
      streamStatus.value = 'error'
      console.error('启动视频流失败:', error)
      throw error
    }
  }
  
  /**
   * 停止视频流
   * @param {string} id - 视频流ID
   */
  async function stopStream(id) {
    try {
      await videosApi.stopVideoStream(id)
      streamStatus.value = 'disconnected'
    } catch (error) {
      console.error('停止视频流失败:', error)
      throw error
    }
  }
  
  /**
   * 获取视频流状态
   * @param {string} id - 视频流ID
   */
  async function fetchStreamStatus(id) {
    try {
      const data = await videosApi.getVideoStatus(id)
      streamStatus.value = data.status
      return data
    } catch (error) {
      console.error('获取视频流状态失败:', error)
      throw error
    }
  }
  
  /**
   * 获取实时缺陷列表
   * @param {Object} params - 查询参数
   */
  async function fetchDefectList(params = {}) {
    defectLoading.value = true
    try {
      const data = await defectsApi.getDefectList(params)
      defectList.value = data.list || data.items || []
    } catch (error) {
      console.error('获取缺陷列表失败:', error)
      throw error
    } finally {
      defectLoading.value = false
    }
  }
  
  /**
   * 获取缺陷统计
   * @param {string} rollId - 布卷ID
   */
  async function fetchDefectStats(rollId) {
    try {
      const data = await defectsApi.getDefectStats(rollId)
      defectStats.value = data
    } catch (error) {
      console.error('获取缺陷统计失败:', error)
      throw error
    }
  }
  
  /**
   * 获取缺陷分类
   * @param {string} rollId - 布卷ID
   */
  async function fetchDefectCategories(rollId) {
    try {
      const data = await defectsApi.getDefectCategories(rollId)
      defectCategories.value = data
    } catch (error) {
      console.error('获取缺陷分类失败:', error)
      throw error
    }
  }
  
  /**
   * 添加实时缺陷（WebSocket推送）
   * @param {Object} defect - 缺陷数据
   */
  function addRealTimeDefect(defect) {
    defectList.value.unshift(defect)
    // 限制列表最大数量，防止内存溢出
    if (defectList.value.length > 100) {
      defectList.value.pop()
    }
  }
  
  /**
   * 更新AI分析状态
   * @param {Object} status - 状态对象
   */
  function updateAIStatus(status) {
    aiAnalysisStatus.value = { ...aiAnalysisStatus.value, ...status }
  }
  
  /**
   * 更新帧率统计
   * @param {Object} fps - 帧率数据
   */
  function updateFpsStats(fps) {
    fpsStats.value = { ...fpsStats.value, ...fps }
  }
  
  /**
   * 清空缺陷列表
   */
  function clearDefectList() {
    defectList.value = []
  }
  
  /**
   * 清空当前选中视频
   */
  function clearCurrentVideo() {
    currentVideo.value = null
  }

  // 导出状态和方法
  return {
    // 视频流状态
    videoList,
    currentVideo,
    streamStatus,
    videoLoading,
    
    // 缺陷状态
    defectList,
    defectStats,
    defectCategories,
    defectLoading,
    
    // 系统状态
    aiAnalysisStatus,
    fpsStats,
    
    // 计算属性
    isInspecting,
    hasDefects,
    criticalDefects,
    
    // 方法
    fetchVideoList,
    fetchVideoDetail,
    startStream,
    stopStream,
    fetchStreamStatus,
    fetchDefectList,
    fetchDefectStats,
    fetchDefectCategories,
    addRealTimeDefect,
    updateAIStatus,
    updateFpsStats,
    clearDefectList,
    clearCurrentVideo
  }
})

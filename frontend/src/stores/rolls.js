/**
 * 布卷管理状态管理
 * 管理布卷列表、详情和相关状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as rollsApi from '@/api/rolls'

/**
 * 布卷管理Store
 * 使用Composition API风格定义
 */
export const useRollsStore = defineStore('rolls', () => {
  // ==================== 状态定义 ====================
  
  // 布卷列表数据
  const rollList = ref([])
  
  // 当前选中的布卷详情
  const currentRoll = ref(null)
  
  // 加载状态
  const loading = ref(false)
  
  // 分页信息
  const pagination = ref({
    page: 1,
    pageSize: 10,
    total: 0
  })
  
  // 查询条件
  const searchParams = ref({
    status: '',
    keyword: ''
  })

  // ==================== 计算属性 ====================
  
  // 统计布卷数量
  const totalRolls = computed(() => rollList.value.length)
  
  // 待验布卷数量
  const pendingRolls = computed(() => 
    rollList.value.filter(roll => roll.status === 'pending').length
  )
  
  // 验布中数量
  const inspectingRolls = computed(() => 
    rollList.value.filter(roll => roll.status === 'inspecting').length
  )
  
  // 已完成数量
  const completedRolls = computed(() => 
    rollList.value.filter(roll => roll.status === 'completed').length
  )

  // ==================== Actions ====================
  
  /**
   * 获取布卷列表
   * @param {Object} params - 查询参数
   */
  async function fetchRollList(params = {}) {
    loading.value = true
    try {
      // 处理分页参数：支持传入 page/pageSize 或直接使用 skip/limit
      const page = params.page || pagination.value.page
      const pageSize = params.pageSize || pagination.value.pageSize
      
      // 构建查询参数，过滤空值并转换分页参数
      const queryParams = {
        page: page,
        pageSize: pageSize
      }
      
      // 添加搜索参数（来自传入参数或store）
      const status = params.status || searchParams.value.status
      const keyword = params.keyword || searchParams.value.keyword
      
      if (status) {
        queryParams.status = status
      }
      if (keyword) {
        queryParams.keyword = keyword
      }
      
      const data = await rollsApi.getRollList(queryParams)
      rollList.value = Array.isArray(data) ? data : (data.list || data.items || [])
      pagination.value.total = data.total || rollList.value.length
    } catch (error) {
      console.error('获取布卷列表失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 获取布卷详情
   * @param {string} id - 布卷ID
   */
  async function fetchRollDetail(id) {
    loading.value = true
    try {
      const data = await rollsApi.getRollDetail(id)
      currentRoll.value = data
      return data
    } catch (error) {
      console.error('获取布卷详情失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 创建布卷
   * @param {Object} data - 布卷数据
   */
  async function createRoll(data) {
    loading.value = true
    try {
      const result = await rollsApi.createRoll(data)
      await fetchRollList()
      return result
    } catch (error) {
      console.error('创建布卷失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 更新布卷
   * @param {string} id - 布卷ID
   * @param {Object} data - 更新数据
   */
  async function updateRoll(id, data) {
    loading.value = true
    try {
      const result = await rollsApi.updateRoll(id, data)
      await fetchRollList()
      // 如果更新的是当前选中的布卷，刷新详情
      if (currentRoll.value?.id === id) {
        await fetchRollDetail(id)
      }
      return result
    } catch (error) {
      console.error('更新布卷失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 删除布卷
   * @param {string} id - 布卷ID
   */
  async function deleteRoll(id) {
    loading.value = true
    try {
      const result = await rollsApi.deleteRoll(id)
      await fetchRollList()
      // 如果删除的是当前选中的布卷，清空选中状态
      if (currentRoll.value?.id === id) {
        currentRoll.value = null
      }
      return result
    } catch (error) {
      console.error('删除布卷失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 开始验布
   * @param {string} id - 布卷ID
   */
  async function startInspection(id) {
    try {
      const result = await rollsApi.startInspection(id)
      await fetchRollList()
      return result
    } catch (error) {
      console.error('开始验布失败:', error)
      throw error
    }
  }
  
  /**
   * 停止验布
   * @param {string} id - 布卷ID
   */
  async function stopInspection(id) {
    try {
      const result = await rollsApi.stopInspection(id)
      await fetchRollList()
      return result
    } catch (error) {
      console.error('停止验布失败:', error)
      throw error
    }
  }
  
  /**
   * 设置查询条件
   * @param {Object} params - 查询条件
   */
  function setSearchParams(params) {
    searchParams.value = { ...searchParams.value, ...params }
    pagination.value.page = 1 // 重置到第一页
  }
  
  /**
   * 设置分页
   * @param {Object} pageConfig - 分页配置
   */
  function setPagination(pageConfig) {
    pagination.value = { ...pagination.value, ...pageConfig }
  }
  
  /**
   * 清空当前选中
   */
  function clearCurrentRoll() {
    currentRoll.value = null
  }

  // 导出状态和方法
  return {
    // 状态
    rollList,
    currentRoll,
    loading,
    pagination,
    searchParams,
    
    // 计算属性
    totalRolls,
    pendingRolls,
    inspectingRolls,
    completedRolls,
    
    // 方法
    fetchRollList,
    fetchRollDetail,
    createRoll,
    updateRoll,
    deleteRoll,
    startInspection,
    stopInspection,
    setSearchParams,
    setPagination,
    clearCurrentRoll
  }
})

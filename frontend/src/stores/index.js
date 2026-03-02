/**
 * Pinia Store 统一导出
 * 导出所有状态管理模块
 */

// 导入各个store模块
import { useRollsStore } from './rolls'
import { useMonitorStore } from './monitor'
import { useVideosStore } from './videos'

/**
 * 统一导出所有store
 * 便于在应用中使用
 */
export {
  useRollsStore,
  useMonitorStore,
  useVideosStore
}

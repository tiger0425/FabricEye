/**
 * API模块统一导出
 * 导出所有API接口模块，便于统一引用
 */

// 导入各模块API
import * as rolls from './rolls'
import * as defects from './defects'
import * as videos from './videos'

/**
 * API集合
 * 包含所有后端API接口调用方法
 */
const api = {
  // 布卷管理相关API
  rolls,
  
  // 缺陷检测相关API
  defects,
  
  // 视频流相关API
  videos
}

// 导出API集合
export default api

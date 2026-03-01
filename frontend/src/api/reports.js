/**
 * 报告管理 API接口
 * 封装与后端报告相关的数据交互
 */
import request from '@/utils/request'

/**
 * 生成布卷报告
 * @param {string|number} rollId - 布卷ID
 * @returns {Promise} 报告数据（含roll、summary、defects、generated_at）
 */
export function generateReport(rollId) {
  return request({
    url: `/rolls/${rollId}/report`,
    method: 'get'
  })
}

/**
 * 获取布卷的缺陷列表
 * @param {string|number} rollId - 布卷ID
 * @param {Object} params - 额外查询参数
 * @returns {Promise} 缺陷列表数据
 */
export function getRollDefects(rollId, params = {}) {
  return request({
    url: '/defects',
    method: 'get',
    params: { rollId, ...params }
  })
}

/**
 * 获取缺陷统计信息
 * @param {string|number} rollId - 布卷ID
 * @returns {Promise} 缺陷统计数据
 */
export function getDefectStats(rollId) {
  return request({
    url: '/defects/stats',
    method: 'get',
    params: { rollId }
  })
}

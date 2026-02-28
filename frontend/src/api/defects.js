/**
 * 缺陷检测 API接口
 * 封装与后端缺陷检测相关的数据交互
 */
import request from '@/utils/request'

/**
 * 获取缺陷列表
 * @param {Object} params - 查询参数
 * @param {string} params.rollId - 布卷ID
 * @param {number} params.page - 页码
 * @param {number} params.pageSize - 每页数量
 * @param {string} params.severity - 缺陷严重程度筛选
 * @returns {Promise} 缺陷列表数据
 */
export function getDefectList(params) {
  return request({
    url: '/defects',
    method: 'get',
    params
  })
}

/**
 * 获取缺陷详情
 * @param {string} id - 缺陷ID
 * @returns {Promise} 缺陷详情数据
 */
export function getDefectDetail(id) {
  return request({
    url: `/defects/${id}`,
    method: 'get'
  })
}

/**
 * 获取缺陷统计信息
 * @param {string} rollId - 布卷ID（可选）
 * @returns {Promise} 缺陷统计数据
 */
export function getDefectStats(rollId) {
  return request({
    url: '/defects/stats',
    method: 'get',
    params: { rollId }
  })
}

/**
 * 获取缺陷分类统计
 * @param {string} rollId - 布卷ID（可选）
 * @returns {Promise} 缺陷分类统计数据
 */
export function getDefectCategories(rollId) {
  return request({
    url: '/defects/categories',
    method: 'get',
    params: { rollId }
  })
}

/**
 * 标记缺陷（人工确认/复核）
 * @param {string} id - 缺陷ID
 * @param {Object} data - 标记数据
 * @returns {Promise} 标记结果
 */
export function markDefect(id, data) {
  return request({
    url: `/defects/${id}/mark`,
    method: 'post',
    data
  })
}

/**
 * 删除缺陷记录
 * @param {string} id - 缺陷ID
 * @returns {Promise} 删除结果
 */
export function deleteDefect(id) {
  return request({
    url: `/defects/${id}`,
    method: 'delete'
  })
}

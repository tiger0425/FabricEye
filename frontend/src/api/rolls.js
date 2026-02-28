/**
 * 布卷管理 API接口
 * 封装与后端布卷相关的数据交互
 */
import request from '@/utils/request'

/**
 * 获取布卷列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.pageSize - 每页数量
 * @param {string} params.status - 布卷状态筛选
 * @returns {Promise} 布卷列表数据
 */
export function getRollList(params) {
  return request({
    url: '/rolls',
    method: 'get',
    params
  })
}

/**
 * 获取布卷详情
 * @param {string} id - 布卷ID
 * @returns {Promise} 布卷详情数据
 */
export function getRollDetail(id) {
  return request({
    url: `/rolls/${id}`,
    method: 'get'
  })
}

/**
 * 创建新布卷
 * @param {Object} data - 布卷数据
 * @returns {Promise} 创建结果
 */
export function createRoll(data) {
  return request({
    url: '/rolls',
    method: 'post',
    data
  })
}

/**
 * 更新布卷信息
 * @param {string} id - 布卷ID
 * @param {Object} data - 更新的数据
 * @returns {Promise} 更新结果
 */
export function updateRoll(id, data) {
  return request({
    url: `/rolls/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除布卷
 * @param {string} id - 布卷ID
 * @returns {Promise} 删除结果
 */
export function deleteRoll(id) {
  return request({
    url: `/rolls/${id}`,
    method: 'delete'
  })
}

/**
 * 开始验布
 * @param {string} id - 布卷ID
 * @returns {Promise} 验布结果
 */
export function startInspection(id) {
  return request({
    url: `/rolls/${id}/start`,
    method: 'post'
  })
}

/**
 * 停止验布
 * @param {string} id - 布卷ID
 * @returns {Promise} 停止结果
 */
export function stopInspection(id) {
  return request({
    url: `/rolls/${id}/stop`,
    method: 'post'
  })
}

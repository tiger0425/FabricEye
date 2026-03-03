/**
 * 级联检测 API 封装
 * 提供级联检测状态查询和报告获取接口
 */
import request from '@/utils/request'

/**
 * 获取布卷的级联检测状态
 * @param {number} rollId - 布卷 ID
 * @returns {Promise<Object>} 级联检测状态数据
 */
export function getCascadeStatus(rollId) {
  return request({
    method: 'GET',
    url: `/rolls/${rollId}/cascade-status`
  })
}

/**
 * 获取布卷检测报告
 * @param {number} rollId - 布卷 ID
 * @returns {Promise<Object>} 检测报告数据
 */
export function getRollReport(rollId) {
  return request({
    method: 'GET',
    url: `/rolls/${rollId}/report`
  })
}

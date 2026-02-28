/**
 * 视频流 API接口
 * 封装与后端视频流相关的数据交互
 */
import request from '@/utils/request'

/**
 * 获取视频流列表
 * @returns {Promise} 视频流列表数据
 */
export function getVideoList() {
  return request({
    url: '/videos',
    method: 'get'
  })
}

/**
 * 获取视频流详情
 * @param {string} id - 视频流ID
 * @returns {Promise} 视频流详情数据
 */
export function getVideoDetail(id) {
  return request({
    url: `/videos/${id}`,
    method: 'get'
  })
}

/**
 * 获取实时视频流地址
 * @param {string} id - 视频流ID
 * @returns {Promise} 视频流地址
 */
export function getVideoStreamUrl(id) {
  return request({
    url: `/videos/${id}/stream`,
    method: 'get'
  })
}

/**
 * 启动视频流
 * @param {string} id - 视频流ID
 * @returns {Promise} 启动结果
 */
export function startVideoStream(id) {
  return request({
    url: `/videos/${id}/start`,
    method: 'post'
  })
}

/**
 * 停止视频流
 * @param {string} id - 视频流ID
 * @returns {Promise} 停止结果
 */
export function stopVideoStream(id) {
  return request({
    url: `/videos/${id}/stop`,
    method: 'post'
  })
}

/**
 * 获取视频流状态
 * @param {string} id - 视频流ID
 * @returns {Promise} 视频流状态数据
 */
export function getVideoStatus(id) {
  return request({
    url: `/videos/${id}/status`,
    method: 'get'
  })
}

/**
 * 获取视频流帧截图
 * @param {string} id - 视频流ID
 * @returns {Promise} 截图数据
 */
export function getVideoSnapshot(id) {
  return request({
    url: `/videos/${id}/snapshot`,
    method: 'get'
  })
}

/**
 * 获取视频录制列表
 * @param {Object} params - 查询参数
 * @param {string} params.rollId - 布卷ID
 * @returns {Promise} 录制列表数据
 */
export function getRecordingList(params) {
  return request({
    url: '/videos/recordings',
    method: 'get',
    params
  })
}

/**
 * 获取视频录制详情
 * @param {string} id - 录制ID
 * @returns {Promise} 录制详情数据
 */
export function getRecordingDetail(id) {
  return request({
    url: `/videos/recordings/${id}`,
    method: 'get'
  })
}

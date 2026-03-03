/**
 * 视频流 API接口
 * 封装与后端视频流相关的数据交互
 */
import request from '@/utils/request'

/**
 * 获取实时视频流地址
 */
export function getVideoStreamUrl(id) {
  return `/api/videos/${id}/stream`
}

/**
 * 启动视频流
 */
export function startVideoStream(id) {
  return request({
    url: `/videos/${id}/start`,
    method: 'post'
  })
}

/**
 * 停止视频流
 */
export function stopVideoStream(id) {
  return request({
    url: `/videos/${id}/stop`,
    method: 'post'
  })
}

/**
 * 获取视频流状态
 */
export function getVideoStatus(id) {
  return request({
    url: `/videos/${id}/status`,
    method: 'get'
  })
}

/**
 * 获取视频流帧截图
 */
export function getVideoSnapshot(id) {
  return request({
    url: `/videos/${id}/snapshot`,
    method: 'get'
  })
}

/**
 * 获取视频详情
 */
export function getVideoDetail(id) {
  return request({
    url: `/videos/${id}/info`,
    method: 'get'
  })
}

/**
 * 获取视频播放URL (直接供 <video src> 使用)
 */
export function getVideoPlayUrl(id) {
  return `/api/videos/stream/${id}`
}

/**
 * 获取视频缺陷列表 (时间轴)
 */
export function getVideoDefects(id) {
  return request({
    url: `/videos/${id}/defects/timeline`,
    method: 'get'
  })
}

/**
 * 生成标记视频 (导出)
 */
export function generateMarkedVideo(id) {
  return request({
    url: `/videos/${id}/export-marked`,
    method: 'post'
  })
}

/**
 * 查询导出状态
 */
export function getExportStatus(taskId) {
  return request({
    url: `/videos/export-status/${taskId}`,
    method: 'get'
  })
}

/**
 * 下载标记视频
 */
export function getMarkedVideoDownloadUrl(taskId) {
  return `/api/videos/download-marked/${taskId}`
}

/**
 * 获取视频流列表 (别名)
 */
export function getVideoList(params) {
  return getRollVideos(params)
}

/**
 * 获取布卷关联的视频列表
 */
export function getRollVideos(params) {
  return request({
    url: '/videos',
    method: 'get',
    params
  })
}

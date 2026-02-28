/**
 * Axios HTTP请求封装
 * 提供统一的请求/响应拦截器和错误处理
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例，配置基础URL和超时时间
const request = axios.create({
  // 后端API基础URL
  baseURL: '/api',
  // 请求超时时间（毫秒）
  timeout: 30000,
  // 请求头配置
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 请求拦截器
 * 在每个请求发送前执行
 */
request.interceptors.request.use(
  (config) => {
    // TODO: 在此处添加认证token等请求头
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    
    // 返回修改后的配置
    return config
  },
  (error) => {
    // 请求错误处理
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 * 在收到响应后执行
 */
request.interceptors.response.use(
  (response) => {
    // 成功响应处理
    const { data } = response
    
    // 根据后端返回的状态码进行处理
    if (data.code !== undefined) {
      if (data.code === 0 || data.code === 200) {
        return data.data
      } else {
        // 显示错误消息
        ElMessage.error(data.message || '请求失败')
        return Promise.reject(new Error(data.message || '请求失败'))
      }
    }
    
    return data
  },
  (error) => {
    // 错误响应处理
    let message = '网络错误，请稍后重试'
    
    if (error.response) {
      // 服务器返回错误状态码
      switch (error.response.status) {
        case 400:
          message = '请求参数错误'
          break
        case 401:
          message = '未授权，请重新登录'
          break
        case 403:
          message = '拒绝访问'
          break
        case 404:
          message = '请求的资源不存在'
          break
        case 500:
          message = '服务器内部错误'
          break
        default:
          message = `请求失败(${error.response.status})`
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      message = '服务器无响应，请检查网络连接'
    }
    
    ElMessage.error(message)
    console.error('响应错误:', error)
    
    return Promise.reject(error)
  }
)

// 导出封装后的axios实例
export default request

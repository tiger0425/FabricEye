/**
 * WebSocket 可复用组合式函数
 * 支持自动连接、断线重连（指数退避）、消息解析
 */
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * useWebSocket - WebSocket 连接管理器
 * @param {string} url - WebSocket 连接 URL
 * @returns {{ status, lastMessage, isConnected, connect, disconnect }}
 */
export function useWebSocket(url) {
  // 连接状态：connecting | connected | disconnected | error
  const status = ref('disconnected')

  // 最新收到的已解析 JSON 消息
  const lastMessage = ref(null)

  // 计算属性：是否已连接
  const isConnected = ref(false)

  // 内部 WebSocket 实例
  let ws = null

  // 重连相关
  let reconnectTimer = null
  let reconnectAttempts = 0
  const MAX_RECONNECT_DELAY = 30000 // 最大重连延迟 30 秒
  const BASE_RECONNECT_DELAY = 1000 // 初始重连延迟 1 秒

  // 是否主动断开（避免手动 disconnect 触发重连）
  let manualDisconnect = false

  /**
   * 计算指数退避重连延迟
   */
  function getReconnectDelay() {
    const delay = BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts)
    return Math.min(delay, MAX_RECONNECT_DELAY)
  }

  /**
   * 建立 WebSocket 连接
   */
  function connect() {
    // 如果已有连接，先关闭
    if (ws) {
      ws.close()
      ws = null
    }

    manualDisconnect = false
    status.value = 'connecting'
    isConnected.value = false

    try {
      ws = new WebSocket(url)

      // 连接成功
      ws.onopen = () => {
        status.value = 'connected'
        isConnected.value = true
        reconnectAttempts = 0 // 重置重连计数
        console.log(`[WebSocket] 已连接: ${url}`)
      }

      // 收到消息
      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data)
          lastMessage.value = parsed
        } catch (e) {
          // 非 JSON 消息，直接存储原始数据
          lastMessage.value = { raw: event.data }
          console.warn('[WebSocket] 收到非 JSON 消息:', event.data)
        }
      }

      // 连接关闭
      ws.onclose = (event) => {
        status.value = 'disconnected'
        isConnected.value = false
        ws = null

        if (!manualDisconnect) {
          // 非主动断开，触发重连
          const delay = getReconnectDelay()
          console.log(`[WebSocket] 连接断开，${delay / 1000}秒后重连（第${reconnectAttempts + 1}次）`)
          reconnectTimer = setTimeout(() => {
            reconnectAttempts++
            connect()
          }, delay)
        } else {
          console.log(`[WebSocket] 已主动断开: ${url}`)
        }
      }

      // 连接错误
      ws.onerror = (error) => {
        status.value = 'error'
        isConnected.value = false
        console.error('[WebSocket] 连接错误:', error)
        // onerror 之后 onclose 会被调用，重连逻辑在 onclose 中处理
      }
    } catch (error) {
      status.value = 'error'
      isConnected.value = false
      console.error('[WebSocket] 创建连接失败:', error)
    }
  }

  /**
   * 主动断开 WebSocket 连接
   */
  function disconnect() {
    manualDisconnect = true

    // 清除重连定时器
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    // 关闭 WebSocket
    if (ws) {
      ws.close()
      ws = null
    }

    status.value = 'disconnected'
    isConnected.value = false
    reconnectAttempts = 0
  }

  // 组件挂载时自动连接
  onMounted(() => {
    connect()
  })

  // 组件卸载时自动断开
  onUnmounted(() => {
    disconnect()
  })

  return {
    status,
    lastMessage,
    isConnected,
    connect,
    disconnect
  }
}

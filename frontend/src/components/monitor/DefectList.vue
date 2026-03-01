<template>
  <div class="defect-list">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-icon class="loading-icon" :size="24"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    
    <!-- 空状态 -->
    <div v-else-if="!defects || defects.length === 0" class="empty-state">
      <el-icon :size="48"><SuccessFilled /></el-icon>
      <span>暂无缺陷</span>
    </div>
    
    <!-- 缺陷列表 -->
    <div v-else class="defect-items">
      <div 
        v-for="defect in defects" 
        :key="defect.id"
        class="defect-item"
        :class="[`severity-${defect.severity}`]"
        @click="handleClick(defect)"
      >
        <!-- 缺陷图片 -->
        <div class="defect-image">
          <img 
            v-if="defect.imageUrl" 
            :src="defect.imageUrl" 
            :alt="defect.type"
          />
          <div v-else class="no-image">
            <el-icon :size="24"><Picture /></el-icon>
          </div>
        </div>
        
        <!-- 缺陷信息 -->
        <div class="defect-info">
          <div class="defect-header">
          <span class="defect-type">{{ getDefectTypeText(defect.defectType || defect.type) }}</span>
            <el-tag :type="getSeverityType(defect.severity)" size="small">
              {{ getSeverityText(defect.severity) }}
            </el-tag>
          </div>
          <div class="defect-detail">
            <span>位置: {{ defect.position || '未知' }}</span>
            <span>置信度: {{ (defect.confidence * 100).toFixed(1) }}%</span>
          </div>
          <div class="defect-time">
            {{ formatTime(defect.timestamp) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import { 
  Loading, 
  SuccessFilled, 
  Picture 
} from '@element-plus/icons-vue'

// 定义Props
const props = defineProps({
  // 缺陷列表
  defects: {
    type: Array,
    default: () => []
  },
  // 加载状态
  loading: {
    type: Boolean,
    default: false
  }
})

// 定义Emits
const emit = defineEmits(['click'])

// 缺陷类型映射
const defectTypeMap = {
  broken_warp: '断经',
  broken_weft: '断纬',
  color_difference: '色差',
  color_variance: '色差',
  color_variation: '色差',
  stain: '污渍',
  damage: '破损',
  hole: '破洞',
  other: '其他'
}

// 严重程度类型映射
const severityTypeMap = {
  critical: 'danger',
  major: 'warning',
  minor: 'info'
}

// 严重程度文本映射
const severityTextMap = {
  critical: '严重',
  major: '主要',
  minor: '次要'
}

/**
 * 获取缺陷类型文本
 */
function getDefectTypeText(type) {
  return defectTypeMap[type] || type
}

/**
 * 获取严重程度类型
 */
function getSeverityType(severity) {
  return severityTypeMap[severity] || 'info'
}

/**
 * 获取严重程度文本
 */
function getSeverityText(severity) {
  return severityTextMap[severity] || '未知'
}

/**
 * 格式化时间
 */
function formatTime(timestamp) {
  if (!timestamp) return ''
  
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }
  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  }
  // 小于24小时
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }
  
  // 格式化日期
  return `${date.getMonth() + 1}-${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
}

/**
 * 处理点击
 */
function handleClick(defect) {
  emit('click', defect)
}
</script>

<style scoped>
.defect-list {
  max-height: 100%;
  overflow-y: auto;
}

/* 加载状态 */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #909399;
}

.loading-icon {
  animation: rotate 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-state {
  color: #67c23a;
}

/* 缺陷列表 */
.defect-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 缺陷项 */
.defect-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: box-shadow 0.2s;
  border-left: 3px solid transparent;
}

.defect-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 严重程度样式 */
.defect-item.severity-critical {
  border-left-color: #f56c6c;
  background-color: #fef0f0;
}

.defect-item.severity-major {
  border-left-color: #e6a23c;
  background-color: #fdf6ec;
}

.defect-item.severity-minor {
  border-left-color: #909399;
}

/* 缺陷图片 */
.defect-image {
  width: 80px;
  height: 60px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.defect-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f7fa;
  color: #c0c4cc;
}

/* 缺陷信息 */
.defect-info {
  flex: 1;
  min-width: 0;
}

.defect-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.defect-type {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.defect-detail {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 3px;
}

.defect-time {
  font-size: 12px;
  color: #c0c4cc;
}
</style>

<template>
  <div class="roll-list">
    <el-table
      v-loading="loading"
      :data="list"
      style="width: 100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="rollNumber" label="布卷号" width="180" />
      <el-table-column prop="fabricType" label="面料类型" width="120">
        <template #default="{ row }">
          {{ getFabricTypeText(row.fabricType) }}
        </template>
      </el-table-column>
      <el-table-column prop="fabricColor" label="面料颜色" width="100" />
      <el-table-column prop="length" label="长度(米)" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="defectCount" label="缺陷数" width="80" />
      <el-table-column prop="createTime" label="创建时间" min-width="180" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleView(row)">
            查看
          </el-button>
          <el-button 
            v-if="row.status === 'pending'" 
            link 
            type="success" 
            size="small"
            @click="handleStart(row)"
          >
            开始
          </el-button>
          <el-button 
            v-if="row.status === 'inspecting'" 
            link 
            type="warning" 
            size="small"
            @click="handleStop(row)"
          >
            停止
          </el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

// 定义Props
const props = defineProps({
  list: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// 定义Emits
const emit = defineEmits(['selection-change', 'view', 'start', 'stop', 'delete'])

// 面料类型映射
const fabricTypeMap = {
  cotton: '棉布',
  silk: '丝绸',
  polyester: '涤纶',
  linen: '麻布',
  wool: '羊毛',
  other: '其他'
}

// 状态类型映射
const statusTypeMap = {
  pending: 'warning',
  inspecting: 'primary',
  completed: 'success',
  failed: 'danger'
}

// 状态文本映射
const statusTextMap = {
  pending: '待验',
  inspecting: '验布中',
  completed: '已完成',
  failed: '失败'
}

/**
 * 获取面料类型文本
 */
function getFabricTypeText(type) {
  return fabricTypeMap[type] || type
}

/**
 * 获取状态类型
 */
function getStatusType(status) {
  return statusTypeMap[status] || 'info'
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
  return statusTextMap[status] || '未知'
}

/**
 * 选择项变化
 */
function handleSelectionChange(selection) {
  emit('selection-change', selection)
}

/**
 * 查看
 */
function handleView(row) {
  emit('view', row)
}

/**
 * 开始验布
 */
function handleStart(row) {
  emit('start', row)
}

/**
 * 停止验布
 */
function handleStop(row) {
  emit('stop', row)
}

/**
 * 删除
 */
function handleDelete(row) {
  emit('delete', row)
}
</script>

<template>
  <div class="report-viewer">
    <!-- 报告基本信息 -->
    <el-descriptions :column="2" border class="report-info">
      <el-descriptions-item label="报告编号">
        {{ reportData?.reportNumber || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="布卷号">
        {{ reportData?.rollNumber || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="报告类型">
        <el-tag>{{ getReportTypeText(reportData?.reportType) }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="生成时间">
        {{ reportData?.createTime || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="验布时长">
        {{ reportData?.inspectionTime || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="质量评分">
        <el-progress 
          :percentage="reportData?.qualityScore || 0" 
          :color="getProgressColor(reportData?.qualityScore)"
        />
      </el-descriptions-item>
    </el-descriptions>

    <!-- 缺陷统计 -->
    <div class="report-section">
      <h3>缺陷统计</h3>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-card total">
            <div class="stat-value">{{ defectStats.total }}</div>
            <div class="stat-label">总缺陷数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card critical">
            <div class="stat-value">{{ defectStats.critical }}</div>
            <div class="stat-label">严重缺陷</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card major">
            <div class="stat-value">{{ defectStats.major }}</div>
            <div class="stat-label">主要缺陷</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card minor">
            <div class="stat-value">{{ defectStats.minor }}</div>
            <div class="stat-label">次要缺陷</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 缺陷分类图表 -->
    <div class="report-section">
      <h3>缺陷分类</h3>
      <div class="category-chart">
        <div 
          v-for="category in defectCategories" 
          :key="category.type"
          class="category-item"
        >
          <div class="category-label">
            <span>{{ category.name }}</span>
            <span>{{ category.count }} ({{ category.percentage }}%)</span>
          </div>
          <el-progress 
            :percentage="category.percentage" 
            :stroke-width="10"
            :show-text="false"
          />
        </div>
      </div>
    </div>

    <!-- 缺陷详情列表 -->
    <div class="report-section">
      <h3>缺陷详情</h3>
      <el-table :data="defectDetails" style="width: 100%">
        <el-table-column prop="type" label="缺陷类型" width="120">
          <template #default="{ row }">
            {{ getDefectTypeText(row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="position" label="位置" width="120" />
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            {{ (row.confidence * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="检测时间" />
      </el-table>
    </div>

    <!-- 备注信息 -->
    <div v-if="reportData?.remark" class="report-section">
      <h3>备注</h3>
      <p>{{ reportData.remark }}</p>
    </div>
  </div>
</template>

<script setup>
import { defineProps, ref } from 'vue'

// 定义Props
const props = defineProps({
  // 报告数据
  reportData: {
    type: Object,
    default: null
  }
})

// 缺陷统计数据（从reportData中提取或模拟）
const defectStats = ref({
  total: props.reportData?.defectCount || 0,
  critical: 0,
  major: 0,
  minor: 0
})

// 缺陷分类数据
const defectCategories = ref([
  { type: 'broken_warp', name: '断经', count: 2, percentage: 40 },
  { type: 'broken_weft', name: '断纬', count: 1, percentage: 20 },
  { type: 'color_difference', name: '色差', count: 1, percentage: 20 },
  { type: 'stain', name: '污渍', count: 1, percentage: 20 }
])

// 缺陷详情列表
const defectDetails = ref([
  {
    id: '1',
    type: 'broken_warp',
    severity: 'critical',
    position: '左侧 2.5米',
    confidence: 0.95,
    timestamp: '2024-01-01 10:30:15'
  }
])

/**
 * 获取报告类型文本
 */
function getReportTypeText(type) {
  const textMap = {
    inspection: '验布报告',
    defect: '缺陷报告',
    statistics: '统计报告'
  }
  return textMap[type] || '未知'
}

/**
 * 获取进度条颜色
 */
function getProgressColor(score) {
  if (score >= 90) return '#67c23a'
  if (score >= 70) return '#e6a23c'
  return '#f56c6c'
}

/**
 * 获取缺陷类型文本
 */
function getDefectTypeText(type) {
  const textMap = {
    broken_warp: '断经',
    broken_weft: '断纬',
    color_difference: '色差',
    stain: '污渍',
    damage: '破损',
    other: '其他'
  }
  return textMap[type] || type
}

/**
 * 获取严重程度类型
 */
function getSeverityType(severity) {
  const typeMap = {
    critical: 'danger',
    major: 'warning',
    minor: 'info'
  }
  return typeMap[severity] || 'info'
}

/**
 * 获取严重程度文本
 */
function getSeverityText(severity) {
  const textMap = {
    critical: '严重',
    major: '主要',
    minor: '次要'
  }
  return textMap[severity] || '未知'
}
</script>

<style scoped>
.report-viewer {
  padding: 20px;
}

.report-info {
  margin-bottom: 30px;
}

.report-section {
  margin-bottom: 30px;
}

.report-section h3 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 15px;
  padding-left: 10px;
  border-left: 3px solid #409eff;
}

/* 统计卡片 */
.stat-card {
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  color: #fff;
}

.stat-card.total {
  background-color: #409eff;
}

.stat-card.critical {
  background-color: #f56c6c;
}

.stat-card.major {
  background-color: #e6a23c;
}

.stat-card.minor {
  background-color: #909399;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
}

.stat-label {
  font-size: 14px;
  margin-top: 5px;
  opacity: 0.9;
}

/* 分类图表 */
.category-chart {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.category-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.category-label {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #606266;
}
</style>

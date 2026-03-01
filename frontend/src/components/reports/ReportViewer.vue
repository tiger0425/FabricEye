<template>
  <div class="report-viewer">
    <!-- 布卷基本信息 -->
    <el-descriptions :column="3" border class="report-info" title="布卷信息">
      <el-descriptions-item label="布卷号">
        {{ roll.roll_number || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="面料类型">
        {{ roll.fabric_type || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="批次号">
        {{ roll.batch_number || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="布卷长度">
        {{ roll.length_meters != null ? `${roll.length_meters} 米` : '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="验布时间">
        {{ formatDate(roll.created_at) }}
      </el-descriptions-item>
      <el-descriptions-item label="报告生成时间">
        {{ formatDate(reportData?.generated_at) }}
      </el-descriptions-item>
    </el-descriptions>

    <!-- 质量评分 -->
    <div class="report-section">
      <h3>质量评分</h3>
      <div class="quality-score-wrap">
        <div class="score-circle" :style="{ borderColor: scoreColor }">
          <span class="score-num" :style="{ color: scoreColor }">{{ qualityScore }}</span>
          <span class="score-unit">分</span>
        </div>
        <div class="score-info">
          <el-tag :type="scoreTagType" size="large" class="score-tag">
            {{ scoreLabel }}
          </el-tag>
          <p class="score-desc">{{ scoreDesc }}</p>
        </div>
      </div>
    </div>

    <!-- 缺陷统计概览 -->
    <div class="report-section">
      <h3>缺陷统计</h3>
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="stat-card total">
            <div class="stat-value">{{ summary.total_defects ?? 0 }}</div>
            <div class="stat-label">总缺陷数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card severe">
            <div class="stat-value">{{ summary.by_severity?.severe ?? 0 }}</div>
            <div class="stat-label">严重</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card moderate">
            <div class="stat-value">{{ summary.by_severity?.moderate ?? 0 }}</div>
            <div class="stat-label">中等</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card minor">
            <div class="stat-value">{{ summary.by_severity?.minor ?? 0 }}</div>
            <div class="stat-label">轻微</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 缺陷类型分布 -->
    <div class="report-section">
      <h3>缺陷类型分布</h3>
      <div v-if="byType.length > 0" class="category-chart">
        <div
          v-for="item in byType"
          :key="item.type"
          class="category-item"
        >
          <div class="category-label">
            <span>{{ getDefectTypeText(item.type) || item.type_cn }}</span>
            <span class="category-count">{{ item.count }} 处（{{ formatPercent(item.percentage) }}%）</span>
          </div>
          <el-progress
            :percentage="item.percentage || 0"
            :stroke-width="10"
            :show-text="false"
          />
        </div>
      </div>
      <el-empty v-else description="暂无缺陷类型数据" :image-size="60" />
    </div>

    <!-- 缺陷详情列表 -->
    <div class="report-section">
      <h3>缺陷详情</h3>
      <el-table
        :data="defects"
        style="width: 100%"
        empty-text="未检测到缺陷"
        stripe
      >
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="defect_type" label="缺陷类型" width="120">
          <template #default="{ row }">
            {{ getDefectTypeText(row.defect_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityTagType(row.severity)" size="small">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            {{ row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="坐标位置" width="160">
          <template #default="{ row }">
            <span v-if="row.bbox_x1 != null">
              ({{ row.bbox_x1 }}, {{ row.bbox_y1 }})
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="frame_number" label="帧编号" width="100">
          <template #default="{ row }">
            {{ row.frame_number ?? '-' }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// 定义Props
const props = defineProps({
  // 报告数据：{ roll, summary, defects, generated_at }
  reportData: {
    type: Object,
    default: null
  }
})

// 缺陷类型映射（英文枚举 → 中文）
const DEFECT_TYPE_MAP = {
  hole: '破洞',
  stain: '污渍',
  color_variance: '色差',
  warp_break: '断经',
  weft_break: '断纬'
}

// 严重程度映射（英文枚举 → 中文）
const SEVERITY_TEXT_MAP = {
  severe: '严重',
  moderate: '中等',
  minor: '轻微'
}

// 严重程度对应 Element Plus Tag 类型
const SEVERITY_TAG_MAP = {
  severe: 'danger',
  moderate: 'warning',
  minor: 'info'
}

// 计算属性：布卷基础信息
const roll = computed(() => props.reportData?.roll || {})
// 计算属性：汇总统计
const summary = computed(() => props.reportData?.summary || {})
// 计算属性：缺陷列表
const defects = computed(() => props.reportData?.defects || [])
// 计算属性：按类型分布
const byType = computed(() => summary.value.by_type || [])
// 计算属性：质量评分
const qualityScore = computed(() => summary.value.quality_score ?? 0)

// 质量评分颜色
const scoreColor = computed(() => {
  const s = qualityScore.value
  if (s >= 90) return '#67c23a'
  if (s >= 70) return '#e6a23c'
  return '#f56c6c'
})

// 质量评分 Tag 类型
const scoreTagType = computed(() => {
  const s = qualityScore.value
  if (s >= 90) return 'success'
  if (s >= 70) return 'warning'
  return 'danger'
})

// 质量等级文字
const scoreLabel = computed(() => {
  const s = qualityScore.value
  if (s >= 90) return '优质'
  if (s >= 70) return '良好'
  return '不合格'
})

// 质量评分描述
const scoreDesc = computed(() => {
  const s = qualityScore.value
  if (s >= 90) return '布卷质量优秀，缺陷极少，可直接出货。'
  if (s >= 70) return '布卷存在少量缺陷，在可接受范围内，建议复核后出货。'
  return '布卷缺陷较多，建议进行人工复检，慎重处理。'
})

/**
 * 获取缺陷类型中文文本
 * @param {string} type - 缺陷类型枚举值
 */
function getDefectTypeText(type) {
  return DEFECT_TYPE_MAP[type] || type || '-'
}

/**
 * 获取严重程度 Tag 类型
 * @param {string} severity - 严重程度枚举值
 */
function getSeverityTagType(severity) {
  return SEVERITY_TAG_MAP[severity] || 'info'
}

/**
 * 获取严重程度中文文本
 * @param {string} severity - 严重程度枚举值
 */
function getSeverityText(severity) {
  return SEVERITY_TEXT_MAP[severity] || severity || '-'
}

/**
 * 格式化日期字符串
 * @param {string} dateStr - ISO 时间字符串
 */
function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

/**
 * 格式化百分比，保留一位小数
 * @param {number} val
 */
function formatPercent(val) {
  if (val == null) return '0.0'
  return Number(val).toFixed(1)
}
</script>

<style scoped>
.report-viewer {
  padding: 10px 4px;
}

.report-info {
  margin-bottom: 28px;
}

.report-section {
  margin-bottom: 28px;
}

.report-section h3 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 3px solid #409eff;
}

/* 质量评分 */
.quality-score-wrap {
  display: flex;
  align-items: center;
  gap: 28px;
  background: #f5f7fa;
  border-radius: 10px;
  padding: 24px 28px;
}

.score-circle {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  border: 6px solid currentColor;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.score-num {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}

.score-unit {
  font-size: 13px;
  opacity: 0.75;
}

.score-tag {
  margin-bottom: 8px;
  font-size: 14px;
}

.score-desc {
  font-size: 14px;
  color: #606266;
  margin: 0;
  line-height: 1.6;
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

.stat-card.severe {
  background-color: #f56c6c;
}

.stat-card.moderate {
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
  margin-top: 6px;
  opacity: 0.9;
}

/* 分类图表 */
.category-chart {
  display: flex;
  flex-direction: column;
  gap: 14px;
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

.category-count {
  color: #909399;
  font-size: 13px;
}
</style>

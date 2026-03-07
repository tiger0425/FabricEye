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
      <el-descriptions-item label="布幅宽度">
        {{ roll.width_cm != null ? `${roll.width_cm} 厘米` : '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="验布时间">
        {{ formatDate(roll.created_at) }}
      </el-descriptions-item>
      <el-descriptions-item label="报告生成时间">
        {{ formatDate(reportData?.generated_at) }}
      </el-descriptions-item>
    </el-descriptions>

    <!-- 四分制评分 (ASTM D5430) -->
    <div class="report-section" v-if="fourPoint">
      <h3>四分制评分 (ASTM D5430)</h3>
      <div class="four-point-wrap">
        <div class="score-circle" :style="{ borderColor: fourPointColor }">
          <span class="score-num" :style="{ color: fourPointColor }">{{ fourPoint.points_per_100sqyd }}</span>
          <span class="score-unit">分/百码²</span>
        </div>
        <div class="score-info">
          <div class="score-main">
            <el-tag :type="fourPointTagType" size="large" class="score-tag">
              {{ fourPoint.grade }}
            </el-tag>
            <span class="pass-status" :class="fourPoint.is_pass ? 'is-pass' : 'not-pass'">
              {{ fourPoint.is_pass ? '合格' : '不合格' }} (及格线: {{ fourPoint.pass_threshold }})
            </span>
          </div>
          <p class="score-desc">
            此布卷总罚分为 <strong>{{ fourPoint.total_points }}</strong> 分。根据布长和布幅换算，每百平方码罚分为 <strong>{{ fourPoint.points_per_100sqyd }}</strong> 分。
          </p>
          <div class="score-dist">
            <span class="dist-label">评分分布：</span>
            <el-tag size="small" type="info" class="dist-tag">1分: {{ fourPoint.score_distribution?.['1分'] || 0 }}</el-tag>
            <el-tag size="small" type="info" class="dist-tag">2分: {{ fourPoint.score_distribution?.['2分'] || 0 }}</el-tag>
            <el-tag size="small" type="info" class="dist-tag">3分: {{ fourPoint.score_distribution?.['3分'] || 0 }}</el-tag>
            <el-tag size="small" type="info" class="dist-tag">4分: {{ fourPoint.score_distribution?.['4分'] || 0 }}</el-tag>
          </div>
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
        <el-table-column prop="confidence" label="置信度" width="80">
          <template #default="{ row }">
            {{ row.confidence != null ? `${(row.confidence * 100).toFixed(0)}%` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="defect_length_cm" label="缺陷长度" width="100">
          <template #default="{ row }">
            {{ row.defect_length_cm != null ? `${row.defect_length_cm.toFixed(1)} cm` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="point_score" label="四分制评分" width="100">
          <template #default="{ row }">
            <span v-if="row.point_score != null" class="score-text" :class="`score-${row.point_score}`">
              {{ row.point_score }} 分
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="位置(距卷首)" min-width="120">
          <template #default="{ row }">
            <span v-if="row.position_meter != null">
              {{ row.position_meter.toFixed(2) }} 米
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

    <!-- 缺陷地图 (Defect Map) -->
    <div class="report-section" v-if="defectsWithPos.length > 0">
      <h3>缺陷地图 (Defect Map)</h3>
      <div class="defect-map">
        <div class="map-track">
          <!-- 刻度线 -->
          <div class="map-tick start"><span class="tick-label">0m</span></div>
          <div class="map-tick end"><span class="tick-label">{{ mapTotalLength.toFixed(0) }}m</span></div>
          <!-- 缺陷标注点 -->
          <div 
            v-for="d in defectsWithPos" 
            :key="d.id"
            class="map-dot"
            :class="`dot-${d.severity || 'minor'}`"
            :style="{ left: `${(d.position_meter / mapTotalLength) * 100}%` }"
          >
            <div class="dot-tooltip">
              <strong>{{ getDefectTypeText(d.defect_type) }}</strong><br>
              位置: {{ d.position_meter.toFixed(2) }}m<br>
              评分: {{ d.point_score || 1 }}分
            </div>
          </div>
        </div>
        <div class="map-legend">
          <span class="legend-item"><span class="dot dot-severe"></span> 严重缺陷</span>
          <span class="legend-item"><span class="dot dot-moderate"></span> 中等缺陷</span>
          <span class="legend-item"><span class="dot dot-minor"></span> 轻微缺陷</span>
        </div>
      </div>
    </div>

    <!-- 严重缺陷证据照片 -->
    <div class="report-section" v-if="severeDefectsWithSnaps.length > 0">
      <h3>严重缺陷证据照片</h3>
      <p class="section-desc">以下照片由 FabricEye 工业相机自动捕获，可作为质量纠纷凭证。</p>
      <el-row :gutter="16">
        <el-col :span="12" v-for="(d, i) in severeDefectsWithSnaps" :key="d.id || i" style="margin-bottom: 16px;">
          <el-card class="snapshot-card" :body-style="{ padding: '0px' }" shadow="hover">
            <div class="snapshot-header">
              <span class="snap-title">[{{ i + 1 }}] {{ getDefectTypeText(d.defect_type) }}</span>
              <span class="snap-meta">{{ d.position_meter?.toFixed(2) }}m · {{ d.defect_length_cm?.toFixed(1) }}cm · {{ d.point_score || 4 }}分</span>
            </div>
            <el-image 
              :src="getSnapshotUrl(d.snapshot_path)" 
              fit="cover" 
              class="snapshot-img"
              :preview-src-list="[getSnapshotUrl(d.snapshot_path)]"
            >
              <template #error>
                <div class="image-slot"><el-icon><Picture /></el-icon> 暂无图片</div>
              </template>
            </el-image>
          </el-card>
        </el-col>
      </el-row>
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
// 计算属性：质量评分 (旧版)
const qualityScore = computed(() => summary.value.quality_score ?? 0)
// 计算属性：四分制评分
const fourPoint = computed(() => summary.value.four_point)

// --- 缺陷地图相关数据 ---
// 具有位置信息的缺陷列表
const defectsWithPos = computed(() => {
  return defects.value.filter(d => d.position_meter != null)
})
// 布卷总长度(用于计算地图比例)
const mapTotalLength = computed(() => {
  return roll.value.length_meters || 100.0
})

// --- 严重缺陷快照相关数据 ---
// 获取有快照照片的严重缺陷
const severeDefectsWithSnaps = computed(() => {
  return defects.value.filter(d => 
    d.severity === 'severe' && 
    d.snapshot_path
  )
})
// 将后端的绝对路径转换为能访问的 HTTP 静态图片 URL
const getSnapshotUrl = (rawPath) => {
  if (!rawPath) return ''
  // rawPath 格式如: E:\...\snapshots\defects\defect_warp_20cm.jpg
  // 我们只取完整文件名 (basename)，拼接后端地址
  const filename = rawPath.split(/[\/\\]/).pop()
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  return `${apiUrl}/snapshots/defects/${filename}`
}

// 四分制颜色
const fourPointColor = computed(() => {
  if (!fourPoint.value) return '#909399'
  if (fourPoint.value.points_per_100sqyd <= 20) return '#67c23a'
  if (fourPoint.value.points_per_100sqyd <= 28) return '#409eff'
  if (fourPoint.value.points_per_100sqyd <= 40) return '#e6a23c'
  return '#f56c6c'
})

// 四分制 Tag 类型
const fourPointTagType = computed(() => {
  if (!fourPoint.value) return 'info'
  if (fourPoint.value.points_per_100sqyd <= 20) return 'success'
  if (fourPoint.value.points_per_100sqyd <= 28) return 'primary'
  if (fourPoint.value.points_per_100sqyd <= 40) return 'warning'
  return 'danger'
})

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

/* 四分制评分专属样式 */
.four-point-wrap {
  display: flex;
  align-items: center;
  gap: 28px;
  background: #fdf6ec;
  border-radius: 10px;
  padding: 24px 28px;
  border: 1px solid #faecd8;
}

.score-main {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.pass-status {
  font-size: 14px;
  font-weight: bold;
}
.pass-status.is-pass {
  color: #67c23a;
}
.pass-status.not-pass {
  color: #f56c6c;
}

.score-dist {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dist-label {
  font-size: 13px;
  color: #909399;
}

.dist-tag {
  background: #fff;
}

/* 表格评分文字颜色 */
.score-text {
  font-weight: bold;
}
.score-1 { color: #909399; }
.score-2 { color: #e6a23c; }
.score-3 { color: #f56c6c; }
.score-4 { color: #c45656; }

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

/* 缺陷地图 (Defect Map) */
.defect-map {
  padding: 10px 20px 30px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-top: 10px;
  overflow: visible;
}

.map-track {
  position: relative;
  height: 8px;
  background: #cbd5e1;
  border-radius: 4px;
  margin: 30px 40px 20px;
}

.map-tick {
  position: absolute;
  top: -6px;
  width: 2px;
  height: 20px;
  background: #94a3b8;
}
.map-tick.start { left: 0; }
.map-tick.end { right: 0; }

.tick-label {
  position: absolute;
  top: 25px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #64748b;
  font-weight: bold;
}

.map-dot {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  border: 2px solid #fff;
  cursor: pointer;
  z-index: 10;
  transition: transform 0.2s;
}
.map-dot:hover {
  transform: translate(-50%, -50%) scale(1.3);
  z-index: 20;
}
.map-dot:hover .dot-tooltip {
  visibility: visible;
  opacity: 1;
}

/* 缺陷点颜色 */
.dot-severe { background-color: #ef4444; }
.dot-moderate { background-color: #f59e0b; }
.dot-minor { background-color: #64748b; }

.dot-tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 23, 42, 0.9);
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  white-space: nowrap;
  pointer-events: none;
  transition: all 0.2s;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.dot-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: rgba(15, 23, 42, 0.9) transparent transparent transparent;
}

.map-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 25px;
  font-size: 13px;
  color: #475569;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-item .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

/* 严重缺陷证据照片 */
.snapshot-card {
  border-color: #fecaca;
  transition: box-shadow 0.3s;
}
.snapshot-card:hover {
  box-shadow: 0 10px 15px -3px rgba(239, 68, 68, 0.2);
}
.snapshot-header {
  padding: 10px 15px;
  background: #fef2f2;
  border-bottom: 1px solid #fee2e2;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.snap-title {
  color: #ef4444;
  font-weight: bold;
  font-size: 14px;
}
.snap-meta {
  color: #7f1d1d;
  font-size: 12px;
}
.snapshot-img {
  width: 100%;
  height: 240px;
  display: block;
}
.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 14px;
}
</style>

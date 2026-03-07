<template>
  <div class="reports-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>报告查看</h2>
      <div class="header-actions">
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 筛选条件 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="布卷号">
          <el-input
            v-model="filterForm.rollNumber"
            placeholder="请输入布卷号"
            clearable
          />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 已完成布卷列表（每卷可生成报告） -->
    <el-card class="list-card">
      <el-table
        v-loading="loading"
        :data="rollList"
        style="width: 100%"
        empty-text="暂无已完成的布卷"
      >
        <el-table-column prop="roll_number" label="布卷号" width="160" />
        <el-table-column prop="fabric_type" label="面料类型" width="120" />
        <el-table-column prop="batch_number" label="批次号" width="140" />
        <el-table-column prop="length_meters" label="长度(米)" width="100">
          <template #default="{ row }">
            {{ row.length_meters ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              :loading="generatingId === row.id"
              @click="handleGenerateReport(row)"
            >
              生成报告
            </el-button>
            <el-button
              link
              type="success"
              :disabled="generatingId === row.id"
              @click="handleViewReport(row)"
            >
              查看报告
            </el-button>
            <el-button
              link
              type="warning"
              :disabled="generatingId === row.id"
              @click="handleDownloadReport(row)"
            >
              导出 PDF
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 报告查看对话框 -->
    <el-dialog
      v-model="viewDialogVisible"
      title="验布报告详情"
      width="85%"
      destroy-on-close
    >
      <div v-loading="reportLoading" class="dialog-content">
        <ReportViewer v-if="currentReportData" :report-data="currentReportData" />
        <el-empty v-else description="暂无报告数据，请先生成报告" />
      </div>
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
        <el-button
          v-if="currentReportData && currentReportData.roll"
          type="primary"
          @click="handleDownloadReport(currentReportData.roll)"
        >
          下载 PDF
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ReportViewer from '@/components/reports/ReportViewer.vue'
import { getRollList } from '@/api/rolls'
import { generateReport } from '@/api/reports'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'

// 加载状态
const loading = ref(false)
const reportLoading = ref(false)
// 当前正在生成报告的布卷ID
const generatingId = ref(null)

// 已完成布卷列表（用于展示报告入口）
const rollList = ref([])

// 筛选表单
const filterForm = reactive({
  rollNumber: '',
  dateRange: []
})

// 分页配置
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 查看对话框
const viewDialogVisible = ref(false)
const currentReportData = ref(null)
// 缓存已生成的报告数据，key 为 rollId
const reportCache = reactive({})

/**
 * 组件挂载时加载数据
 */
onMounted(() => {
  loadData()
})

/**
 * 加载已完成布卷列表
 */
async function loadData() {
  loading.value = true
  try {
    const params = {
      status: 'completed',
      page: pagination.page,
      pageSize: pagination.pageSize
    }
    if (filterForm.rollNumber) {
      params.roll_number = filterForm.rollNumber
    }
    if (filterForm.dateRange && filterForm.dateRange.length === 2) {
      params.start_date = filterForm.dateRange[0]
      params.end_date = filterForm.dateRange[1]
    }

    const data = await getRollList(params)
    // 后端可能返回分页对象 { list, total } 或者直接数组
    if (Array.isArray(data)) {
      rollList.value = data
      pagination.total = data.length
    } else {
      rollList.value = data.list || data.items || []
      pagination.total = data.total || rollList.value.length
    }
  } catch (error) {
    console.error('加载布卷列表失败:', error)
    ElMessage.error('加载数据失败，请刷新重试')
  } finally {
    loading.value = false
  }
}

/**
 * 生成并预览报告
 * @param {Object} row - 布卷行数据
 */
async function handleGenerateReport(row) {
  generatingId.value = row.id
  try {
    const data = await generateReport(row.id)
    reportCache[row.id] = data
    currentReportData.value = data
    viewDialogVisible.value = true
    ElMessage.success('报告生成成功')
  } catch (error) {
    console.error('生成报告失败:', error)
    ElMessage.error('报告生成失败，请稍后重试')
  } finally {
    generatingId.value = null
  }
}

/**
 * 查看已生成的报告（若有缓存直接展示，否则触发生成）
 * @param {Object} row - 布卷行数据
 */
async function handleViewReport(row) {
  if (reportCache[row.id]) {
    currentReportData.value = reportCache[row.id]
    viewDialogVisible.value = true
    return
  }
  // 无缓存则触发生成
  viewDialogVisible.value = true
  currentReportData.value = null
  reportLoading.value = true
  try {
    const data = await generateReport(row.id)
    reportCache[row.id] = data
    currentReportData.value = data
  } catch (error) {
    console.error('获取报告失败:', error)
    ElMessage.error('获取报告失败，请稍后重试')
    viewDialogVisible.value = false
  } finally {
    reportLoading.value = false
  }
}

/**
 * 直接下载报告为 PDF（调用后端接口）
 * @param {Object} row - 布卷行数据
 */
// 处理"下载"报告按钮点击事件
const handleDownloadReport = (row) => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  // 修改为直接打开后端的 PDF 下载接口，增加时间戳防止浏览器缓存
  // 修正 API 路径，去除不存在的 /v1
  const pdfUrl = `${apiUrl}/api/rolls/${row.id}/report/pdf?t=${Date.now()}`
  
  // 提示用户正在下载
  ElMessage.success(`开始下载 ${row.roll_number} 的验布报告...`)
  
  // 使用隐藏的 <a> 标签触发下载
  const a = document.createElement('a')
  a.href = pdfUrl
  a.setAttribute('download', '') // 尝试触发下载而非在当前页面打开
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}


/**
 * 生成并下载自包含 HTML 报告文件
 * @param {Object} reportData - 报告数据（含 roll、summary、defects、generated_at）
 */
function downloadHtmlReport(reportData) {
  const roll = reportData?.roll || {}
  const summary = reportData?.summary || {}
  const defects = reportData?.defects || []
  const generatedAt = reportData?.generated_at
    ? formatDate(reportData.generated_at)
    : formatDate(new Date().toISOString())

  const severityMap = { severe: '严重', moderate: '中等', minor: '轻微' }
  const defectTypeMap = {
    hole: '破洞',
    stain: '污渍',
    color_variance: '色差',
    warp_break: '断经',
    weft_break: '断纬'
  }

  const qualityScore = summary.quality_score ?? 0
  const scoreColor = qualityScore >= 90 ? '#22c55e' : qualityScore >= 70 ? '#f59e0b' : '#ef4444'

  const fourPoint = summary.four_point
  let fourPointColor = '#94a3b8'
  if (fourPoint) {
    if (fourPoint.points_per_100sqyd <= 20) fourPointColor = '#22c55e'
    else if (fourPoint.points_per_100sqyd <= 28) fourPointColor = '#3b82f6'
    else if (fourPoint.points_per_100sqyd <= 40) fourPointColor = '#f59e0b'
    else fourPointColor = '#ef4444'
  }

  // 构建缺陷类型分布行
  const byTypeRows = (summary.by_type || [])
    .map(
      (t) => `
      <tr>
        <td>${defectTypeMap[t.type] || t.type_cn || t.type}</td>
        <td>${t.count}</td>
        <td>${t.percentage?.toFixed(1) ?? '-'}%</td>
      </tr>`
    )
    .join('')

  // 构建缺陷详情行
  const defectRows = defects
    .map(
      (d, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${defectTypeMap[d.defect_type] || d.defect_type || '-'}</td>
        <td class="severity-${d.severity}">${severityMap[d.severity] || d.severity || '-'}</td>
        <td>${((d.confidence || 0) * 100).toFixed(1)}%</td>
        <td>${d.defect_length_cm != null ? `${d.defect_length_cm.toFixed(1)} cm` : '-'}</td>
        <td class="score-text score-${d.point_score}">${d.point_score != null ? `${d.point_score} 分` : '-'}</td>
        <td>${d.position_meter != null ? `${d.position_meter.toFixed(2)} 米` : '-'}</td>
      </tr>`
    )
    .join('')

  const htmlContent = `
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    .pdf-container {
      font-family: 'PingFang SC', 'Microsoft YaHei', '微软雅黑', sans-serif;
      background: #fff;
      color: #1a202c;
      padding: 40px;
      width: 900px;
    }
    .report-wrap {
      width: 100%;
      background: #fff;
      overflow: hidden;
    }
    /* 头部 */
    .report-header {
      background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
      color: #fff;
      padding: 36px 40px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-radius: 8px 8px 0 0;
    }
    .brand { font-size: 28px; font-weight: 800; letter-spacing: 2px; }
    .brand span { color: #93c5fd; }
    .brand-sub { font-size: 13px; opacity: .7; margin-top: 4px; }
    .report-meta { text-align: right; font-size: 13px; opacity: .85; line-height: 1.8; }
    /* 内容区 */
    .report-body { padding: 36px 40px; }
    /* 分区 */
    .section { margin-bottom: 36px; }
    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: #1e3a5f;
      padding-bottom: 10px;
      border-bottom: 2px solid #2563eb;
      margin-bottom: 18px;
    }
    /* 基本信息 grid */
    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
    }
    .info-item { background: #f0f4ff; border-radius: 8px; padding: 14px 16px; }
    .info-label { font-size: 12px; color: #64748b; margin-bottom: 4px; }
    .info-value { font-size: 15px; font-weight: 600; color: #1e3a5f; }
    /* 质量评分 */
    .score-section {
      display: flex;
      align-items: center;
      gap: 24px;
      background: #f8fafc;
      border-radius: 12px;
      padding: 24px 28px;
    }
    .score-ring {
      width: 90px;
      height: 90px;
      border-radius: 50%;
      border: 6px solid ${scoreColor};
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .score-number { font-size: 26px; font-weight: 800; color: ${scoreColor}; }
    .score-label { font-size: 13px; color: #64748b; margin-top: 2px; }
    .score-desc { font-size: 14px; color: #475569; line-height: 1.7; }
    /* 统计卡片 */
    .stats-row { display: flex; gap: 16px; }
    .stat-card {
      flex: 1;
      border-radius: 10px;
      padding: 20px;
      text-align: center;
      color: #fff;
    }
    .stat-card.total { background: #2563eb; }
    .stat-card.severe { background: #ef4444; }
    .stat-card.moderate { background: #f59e0b; }
    .stat-card.minor { background: #6b7280; }
    .stat-num { font-size: 32px; font-weight: 800; }
    .stat-lbl { font-size: 13px; opacity: .85; margin-top: 4px; }
    /* 表格 */
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th {
      background: #1e3a5f;
      color: #fff;
      padding: 12px 14px;
      text-align: left;
      font-weight: 600;
    }
    td { padding: 11px 14px; border-bottom: 1px solid #e2e8f0; color: #334155; }
    tr:last-child td { border-bottom: none; }
    tr:nth-child(even) td { background: #f8fafc; }
    .severity-severe { color: #ef4444; font-weight: 600; }
    .severity-moderate { color: #f59e0b; font-weight: 600; }
    .severity-minor { color: #6b7280; }
    .score-text { font-weight: 600; text-align: center; }
    .score-1 { color: #64748b; }
    .score-2 { color: #f59e0b; }
    .score-3 { color: #ef4444; }
    .score-4 { color: #b91c1c; }
    /* 页脚 */
    .report-footer {
      background: #f0f4ff;
      padding: 20px 40px;
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #94a3b8;
      border-top: 1px solid #e2e8f0;
      border-radius: 0 0 8px 8px;
    }
  </style>
  <div class="pdf-container">
  <div class="report-wrap">
    <!-- 报告头部 -->
    <div class="report-header">
      <div>
        <div class="brand">Fabric<span>Eye</span></div>
        <div class="brand-sub">AI 智能验布系统</div>
      </div>
      <div class="report-meta">
        <div>布卷号：${roll.roll_number || '-'}</div>
        <div>批次号：${roll.batch_number || '-'}</div>
        <div>生成时间：${generatedAt}</div>
      </div>
    </div>

    <div class="report-body">
      <!-- 布卷基本信息 -->
      <div class="section">
        <div class="section-title">布卷信息</div>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">布卷号</div>
            <div class="info-value">${roll.roll_number || '-'}</div>
          </div>
          <div class="info-item">
            <div class="info-label">面料类型</div>
            <div class="info-value">${roll.fabric_type || '-'}</div>
          </div>
          <div class="info-item">
            <div class="info-label">批次号</div>
            <div class="info-value">${roll.batch_number || '-'}</div>
          </div>
          <div class="info-item">
            <div class="info-label">长度（米）</div>
            <div class="info-value">${roll.length_meters ?? '-'}</div>
          </div>
          <div class="info-item">
            <div class="info-label">布幅（厘米）</div>
            <div class="info-value">${roll.width_cm ?? '-'}</div>
          </div>
          <div class="info-item">
            <div class="info-label">布卷状态</div>
            <div class="info-value">已完成</div>
          </div>
          <div class="info-item">
            <div class="info-label">验布时间</div>
            <div class="info-value">${formatDate(roll.created_at)}</div>
          </div>
        </div>
      </div>

      <!-- 四分制评分 -->
      ${
        fourPoint
          ? `<div class="section">
        <div class="section-title">四分制评分 (ASTM D5430)</div>
        <div class="score-section" style="background:#fdf6ec; border:1px solid #faecd8;">
          <div class="score-ring" style="border-color:${fourPointColor}">
            <div class="score-number" style="color:${fourPointColor}">${fourPoint.points_per_100sqyd}</div>
          </div>
          <div>
            <div class="score-label" style="display:flex; align-items:center; gap:10px;">
              <span style="font-size:16px; font-weight:bold; color:#1e3a5f;">${fourPoint.grade}</span>
              <span style="color:${fourPoint.is_pass ? '#22c55e' : '#ef4444'}; font-weight:bold;">
                ${fourPoint.is_pass ? '合格' : '不合格'} (及格线: ${fourPoint.pass_threshold})
              </span>
            </div>
            <div class="score-desc" style="margin-top:6px;">
              总罚分: <strong>${fourPoint.total_points}</strong> 分。分布: [1分: ${fourPoint.score_distribution?.['1分']||0}, 2分: ${fourPoint.score_distribution?.['2分']||0}, 3分: ${fourPoint.score_distribution?.['3分']||0}, 4分: ${fourPoint.score_distribution?.['4分']||0}]
            </div>
          </div>
        </div>
      </div>`
          : ''
      }



      <!-- 缺陷统计 -->
      <div class="section">
        <div class="section-title">缺陷统计</div>
        <div class="stats-row">
          <div class="stat-card total">
            <div class="stat-num">${summary.total_defects ?? 0}</div>
            <div class="stat-lbl">总缺陷数</div>
          </div>
          <div class="stat-card severe">
            <div class="stat-num">${summary.by_severity?.severe ?? 0}</div>
            <div class="stat-lbl">严重</div>
          </div>
          <div class="stat-card moderate">
            <div class="stat-num">${summary.by_severity?.moderate ?? 0}</div>
            <div class="stat-lbl">中等</div>
          </div>
          <div class="stat-card minor">
            <div class="stat-num">${summary.by_severity?.minor ?? 0}</div>
            <div class="stat-lbl">轻微</div>
          </div>
        </div>
      </div>

      <!-- 缺陷类型分布 -->
      ${
        (summary.by_type || []).length > 0
          ? `<div class="section">
        <div class="section-title">缺陷类型分布</div>
        <table>
          <thead>
            <tr><th>缺陷类型</th><th>数量</th><th>占比</th></tr>
          </thead>
          <tbody>${byTypeRows}</tbody>
        </table>
      </div>`
          : ''
      }

      <!-- 缺陷详情 -->
      ${
        defects.length > 0
          ? `<div class="section">
        <div class="section-title">缺陷详情列表</div>
        <table>
          <thead>
            <tr><th>#</th><th>缺陷类型</th><th>严重程度</th><th>置信度</th><th>缺陷长度</th><th>评分</th><th>位置(距卷首)</th></tr>
          </thead>
          <tbody>${defectRows}</tbody>
        </table>
      </div>`
          : `<div class="section">
        <div class="section-title">缺陷详情列表</div>
        <p style="color:#94a3b8;text-align:center;padding:24px 0;">未检测到缺陷</p>
      </div>`
      }
    </div>

    <!-- 报告页脚 -->
    <div class="report-footer">
      <span>FabricEye AI 验布系统 · 自动生成报告</span>
      <span>生成时间：${generatedAt}</span>
    </div>
  </div>
  </div>
  `;

  // 重新构建给 html2pdf 解析使用的完整 DOM 树，且赋予固定宽度防止其截图时塌陷导致只有 3KB 乱码
  const container = document.createElement('div');
  container.innerHTML = htmlContent;
  container.style.width = '900px'; 
  container.style.padding = '20px';
  container.style.backgroundColor = '#fff';
  
  // 关键修复：必须挂载到 DOM 树中并且脱离视口，html2canvas 才能计算样式并截图
  container.style.position = 'fixed';
  container.style.left = '-9999px';
  document.body.appendChild(container);

  const reportName = `验布报告-${roll.roll_number || 'unknown'}-${new Date().toISOString().slice(0, 10)}.pdf`;
  ElMessage.info('正在提取数据层生成 PDF，请稍等...');
  
  // 通过其底层的 html2canvas 渲染 dom 到图像，然后由 jsPDF 封包为干净的 PDF，这是最彻底能修复名字及大小畸变的方法
  html2canvas(container, {
    scale: 2, 
    useCORS: true, 
    logging: false,
    backgroundColor: '#ffffff'
  }).then((canvas) => {
    // 换取渲染后的高画质 base64 图像
    const imgData = canvas.toDataURL('image/jpeg', 1.0);
    
    // a4纸张的长宽计算 (单位mm)
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    
    // 在生成的 PDF 中将图片贴上去
    pdf.addImage(imgData, 'JPEG', 0, 0, pdfWidth, pdfHeight);
    
    // 强制获取二进制文件流
    const pdfBlob = pdf.output('blob');
    
    // 使用原生的 URL Object 与 <a> 标签指定下载名字并模拟点击
    const url = URL.createObjectURL(pdfBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = reportName; // 强制赋予真实的系统级文件名
    document.body.appendChild(link);
    link.click();
    
    // 清理创建的资源
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    ElMessage.success('PDF 现已下发保存！');
    document.body.removeChild(container);
  }).catch((err) => {
    console.error('PDF生成失败:', err);
    ElMessage.error('转换 PDF 失败');
    if (document.body.contains(container)) {
      document.body.removeChild(container);
    }
  });
}

/**
 * 格式化日期字符串
 * @param {string} dateStr - ISO 时间字符串
 * @returns {string} 格式化后的日期
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
 * 搜索
 */
function handleSearch() {
  pagination.page = 1
  loadData()
}

/**
 * 重置
 */
function handleReset() {
  filterForm.rollNumber = ''
  filterForm.dateRange = []
  pagination.page = 1
  loadData()
}

/**
 * 刷新
 */
function handleRefresh() {
  loadData()
  ElMessage.success('刷新成功')
}

/**
 * 分页大小变化
 */
function handleSizeChange(size) {
  pagination.pageSize = size
  loadData()
}

/**
 * 页码变化
 */
function handlePageChange(page) {
  pagination.page = page
  loadData()
}
</script>

<style scoped>
.reports-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-card {
  margin-bottom: 20px;
}

.list-card {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.dialog-content {
  min-height: 200px;
}
</style>

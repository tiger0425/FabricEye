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
        <el-form-item label="报告类型">
          <el-select v-model="filterForm.reportType" placeholder="全部" clearable>
            <el-option label="验布报告" value="inspection" />
            <el-option label="缺陷报告" value="defect" />
            <el-option label="统计报告" value="statistics" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 报告列表 -->
    <el-card class="list-card">
      <el-table 
        v-loading="loading" 
        :data="reportList" 
        style="width: 100%"
      >
        <el-table-column prop="reportNumber" label="报告编号" width="180" />
        <el-table-column prop="rollNumber" label="布卷号" width="150" />
        <el-table-column prop="reportType" label="报告类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ getReportTypeText(row.reportType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="defectCount" label="缺陷数量" width="100" />
        <el-table-column prop="qualityScore" label="质量评分" width="100">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.qualityScore" 
              :color="getProgressColor(row.qualityScore)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="inspectionTime" label="验布时长" width="100" />
        <el-table-column prop="createTime" label="生成时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="success" @click="handleDownload(row)">下载</el-button>
            <el-button link type="info" @click="handleExport(row)">导出</el-button>
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
      title="报告详情"
      width="80%"
      destroy-on-close
    >
      <ReportViewer :report-data="currentReport" />
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleDownload(currentReport)">下载报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ReportViewer from '@/components/reports/ReportViewer.vue'

// 加载状态
const loading = ref(false)

// 报告列表数据
const reportList = ref([
  {
    id: '1',
    reportNumber: 'RPT-20240101-001',
    rollNumber: 'RL-20240101-001',
    reportType: 'inspection',
    defectCount: 5,
    qualityScore: 92,
    inspectionTime: '45分钟',
    createTime: '2024-01-01 12:00:00'
  }
])

// 筛选表单
const filterForm = reactive({
  rollNumber: '',
  dateRange: [],
  reportType: ''
})

// 分页配置
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 1
})

// 查看对话框
const viewDialogVisible = ref(false)
const currentReport = ref(null)

/**
 * 组件挂载时加载数据
 */
onMounted(() => {
  loadData()
})

/**
 * 加载数据
 */
async function loadData() {
  loading.value = true
  try {
    // TODO: 调用API获取报告列表
    // const data = await getReportList(...)
    // reportList.value = data.list
    // pagination.total = data.total
  } catch (error) {
    console.error('加载报告列表失败:', error)
  } finally {
    loading.value = false
  }
}

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
  filterForm.reportType = ''
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
 * 查看报告
 */
function handleView(row) {
  currentReport.value = row
  viewDialogVisible.value = true
}

/**
 * 下载报告
 */
function handleDownload(row) {
  // TODO: 实现报告下载
  ElMessage.info('下载功能开发中')
}

/**
 * 导出报告
 */
function handleExport(row) {
  // TODO: 实现报告导出
  ElMessage.info('导出功能开发中')
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
</style>

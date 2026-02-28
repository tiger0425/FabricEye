<template>
  <div class="rolls-view">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <h2>布卷管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon>
          新建布卷
        </el-button>
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 搜索筛选区域 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部状态" clearable>
            <el-option label="待验" value="pending" />
            <el-option label="验布中" value="inspecting" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input 
            v-model="filterForm.keyword" 
            placeholder="布卷号/面料类型" 
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 布卷列表 -->
    <el-card class="list-card">
      <el-table 
        v-loading="rollsStore.loading" 
        :data="rollsStore.rollList" 
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="rollNumber" label="布卷号" width="180" />
        <el-table-column prop="fabricType" label="面料类型" width="150" />
        <el-table-column prop="fabricColor" label="面料颜色" width="120" />
        <el-table-column prop="length" label="长度(米)" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="defectCount" label="缺陷数" width="100" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button 
              v-if="row.status === 'pending'" 
              link 
              type="success" 
              @click="handleStart(row)"
            >
              开始验布
            </el-button>
            <el-button 
              v-if="row.status === 'inspecting'" 
              link 
              type="warning" 
              @click="handleStop(row)"
            >
              停止
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="rollsStore.pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 布卷表单对话框 -->
    <RollForm
      v-model="formVisible"
      :roll-data="currentRoll"
      @success="handleFormSuccess"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRollsStore } from '@/stores'
import { ElMessage, ElMessageBox } from 'element-plus'
import RollForm from '@/components/rolls/RollForm.vue'

const rollsStore = useRollsStore()

// 筛选表单
const filterForm = reactive({
  status: '',
  keyword: ''
})

// 分页配置
const pagination = reactive({
  page: 1,
  pageSize: 10
})

// 表单对话框
const formVisible = ref(false)
const currentRoll = ref(null)
const selectedRows = ref([])

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
  await rollsStore.fetchRollList({
    page: pagination.page,
    pageSize: pagination.pageSize,
    ...filterForm
  })
}

/**
 * 获取状态类型
 */
function getStatusType(status) {
  const typeMap = {
    pending: 'warning',
    inspecting: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
  const textMap = {
    pending: '待验',
    inspecting: '验布中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || '未知'
}

/**
 * 搜索
 */
function handleSearch() {
  pagination.page = 1
  loadData()
}

/**
 * 重置筛选
 */
function handleReset() {
  filterForm.status = ''
  filterForm.keyword = ''
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
 * 新建布卷
 */
function handleAdd() {
  currentRoll.value = null
  formVisible.value = true
}

/**
 * 查看布卷详情
 */
function handleView(row) {
  // TODO: 跳转到详情页或打开详情对话框
  console.log('查看布卷:', row)
}

/**
 * 开始验布
 */
async function handleStart(row) {
  try {
    await rollsStore.startInspection(row.id)
    ElMessage.success('已启动验布')
    loadData()
  } catch (error) {
    ElMessage.error('启动验布失败')
  }
}

/**
 * 停止验布
 */
async function handleStop(row) {
  try {
    await rollsStore.stopInspection(row.id)
    ElMessage.success('已停止验布')
    loadData()
  } catch (error) {
    ElMessage.error('停止验布失败')
  }
}

/**
 * 删除布卷
 */
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该布卷吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await rollsStore.deleteRoll(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

/**
 * 选择项变化
 */
function handleSelectionChange(rows) {
  selectedRows.value = rows
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

/**
 * 表单提交成功
 */
function handleFormSuccess() {
  formVisible.value = false
  loadData()
}
</script>

<style scoped>
.rolls-view {
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

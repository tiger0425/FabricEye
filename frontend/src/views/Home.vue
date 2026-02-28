<template>
  <div class="home-view">
    <!-- 欢迎标题 -->
    <div class="welcome-section">
      <h1>欢迎使用 FabricEye AI验布系统</h1>
      <p class="subtitle">智能面料缺陷检测与管理平台</p>
    </div>

    <!-- 统计卡片区域 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409eff">
              <el-icon :size="32"><Box /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalRolls }}</div>
              <div class="stat-label">总布卷数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #e6a23c">
              <el-icon :size="32"><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pendingRolls }}</div>
              <div class="stat-label">待验布卷</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67c23a">
              <el-icon :size="32"><Loading /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.inspectingRolls }}</div>
              <div class="stat-label">验布中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #909399">
              <el-icon :size="32"><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.completedRolls }}</div>
              <div class="stat-label">已完成</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作区域 -->
    <el-row :gutter="20" class="action-row">
      <el-col :span="24">
        <el-card class="action-card">
          <template #header>
            <div class="card-header">
              <span>快捷操作</span>
            </div>
          </template>
          <div class="action-buttons">
            <el-button type="primary" @click="handleQuickAction('newRoll')">
              <el-icon><Plus /></el-icon>
              新建布卷
            </el-button>
            <el-button type="success" @click="handleQuickAction('startMonitor')">
              <el-icon><VideoCamera /></el-icon>
              开始监控
            </el-button>
            <el-button type="info" @click="handleQuickAction('viewReports')">
              <el-icon><Document /></el-icon>
              查看报告
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近布卷列表 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="recent-card">
          <template #header>
            <div class="card-header">
              <span>最近布卷</span>
              <el-button text @click="goToRolls">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentRolls" style="width: 100%">
            <el-table-column prop="rollNumber" label="布卷号" width="180" />
            <el-table-column prop="fabricType" label="面料类型" width="150" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="defectCount" label="缺陷数" width="100" />
            <el-table-column prop="createTime" label="创建时间" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRollsStore } from '@/stores'

const router = useRouter()
const rollsStore = useRollsStore()

// 统计数据
const stats = ref({
  totalRolls: 0,
  pendingRolls: 0,
  inspectingRolls: 0,
  completedRolls: 0
})

// 最近布卷列表
const recentRolls = ref([])

/**
 * 组件挂载时获取数据
 */
onMounted(async () => {
  await loadData()
})

/**
 * 加载首页数据
 */
async function loadData() {
  try {
    // 获取布卷列表
    await rollsStore.fetchRollList({ page: 1, pageSize: 5 })
    
    // 更新统计数据
    stats.value = {
      totalRolls: rollsStore.totalRolls,
      pendingRolls: rollsStore.pendingRolls,
      inspectingRolls: rollsStore.inspectingRolls,
      completedRolls: rollsStore.completedRolls
    }
    
    // 更新最近布卷
    recentRolls.value = rollsStore.rollList
  } catch (error) {
    console.error('加载数据失败:', error)
  }
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
 * 处理快捷操作
 */
function handleQuickAction(action) {
  switch (action) {
    case 'newRoll':
      router.push('/rolls?action=new')
      break
    case 'startMonitor':
      router.push('/monitor')
      break
    case 'viewReports':
      router.push('/reports')
      break
  }
}

/**
 * 跳转到布卷管理页面
 */
function goToRolls() {
  router.push('/rolls')
}
</script>

<style scoped>
.home-view {
  padding: 20px;
}

.welcome-section {
  margin-bottom: 30px;
}

.welcome-section h1 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 10px;
}

.subtitle {
  font-size: 14px;
  color: #909399;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-right: 15px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.action-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 15px;
}

.recent-card {
  margin-top: 20px;
}
</style>

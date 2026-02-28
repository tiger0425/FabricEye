<template>
  <div class="settings-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>系统设置</h2>
    </div>

    <!-- 设置内容 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <!-- 基础设置 -->
        <el-card class="settings-card">
          <template #header>
            <span>基础设置</span>
          </template>
          <el-form :model="settingsForm" label-width="120px">
            <el-form-item label="系统名称">
              <el-input v-model="settingsForm.systemName" />
            </el-form-item>
            <el-form-item label="自动验布">
              <el-switch v-model="settingsForm.autoInspection" />
            </el-form-item>
            <el-form-item label="缺陷阈值">
              <el-slider 
                v-model="settingsForm.defectThreshold" 
                :min="0" 
                :max="100"
                show-input
              />
            </el-form-item>
            <el-form-item label="视频保存天数">
              <el-input-number 
                v-model="settingsForm.videoRetentionDays" 
                :min="1" 
                :max="90"
              />
              <span class="form-tip">天</span>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- AI模型设置 -->
        <el-card class="settings-card">
          <template #header>
            <span>AI模型设置</span>
          </template>
          <el-form :model="aiSettingsForm" label-width="120px">
            <el-form-item label="模型选择">
              <el-select v-model="aiSettingsForm.modelType">
                <el-option label="YOLOv8" value="yolov8" />
                <el-option label="ResNet50" value="resnet50" />
                <el-option label="EfficientNet" value="efficientnet" />
              </el-select>
            </el-form-item>
            <el-form-item label="置信度阈值">
              <el-slider 
                v-model="aiSettingsForm.confidenceThreshold" 
                :min="0" 
                :max="100"
                :format-tooltip="val => val + '%'"
              />
            </el-form-item>
            <el-form-item label="实时推理">
              <el-switch v-model="aiSettingsForm.realTimeInference" />
            </el-form-item>
            <el-form-item label="缺陷分类">
              <el-checkbox-group v-model="aiSettingsForm.defectCategories">
                <el-checkbox label="断经">断经</el-checkbox>
                <el-checkbox label="断纬">断纬</el-checkbox>
                <el-checkbox label="色差">色差</el-checkbox>
                <el-checkbox label="污渍">污渍</el-checkbox>
                <el-checkbox label="破损">破损</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 保存按钮 -->
        <div class="save-section">
          <el-button type="primary" @click="handleSave" :loading="saving">
            保存设置
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>
      </el-col>

      <el-col :span="8">
        <!-- 系统信息 -->
        <el-card class="info-card">
          <template #header>
            <span>系统信息</span>
          </template>
          <div class="info-content">
            <div class="info-item">
              <span class="label">系统版本:</span>
              <span class="value">v1.0.0</span>
            </div>
            <div class="info-item">
              <span class="label">前端框架:</span>
              <span class="value">Vue 3 + Vite</span>
            </div>
            <div class="info-item">
              <span class="label">UI组件库:</span>
              <span class="value">Element Plus</span>
            </div>
            <div class="info-item">
              <span class="label">后端API:</span>
              <span class="value">http://localhost:8000</span>
            </div>
          </div>
        </el-card>

        <!-- 关于 -->
        <el-card class="about-card">
          <template #header>
            <span>关于</span>
          </template>
          <div class="about-content">
            <p>FabricEye AI验布系统</p>
            <p>一款基于人工智能的面料缺陷检测系统</p>
            <p>帮助小微面料商实现自动化验布</p>
            <p class="copyright">© 2024 FabricEye</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

// 保存状态
const saving = ref(false)

// 基础设置表单
const settingsForm = reactive({
  systemName: 'FabricEye AI验布系统',
  autoInspection: true,
  defectThreshold: 50,
  videoRetentionDays: 7
})

// AI模型设置表单
const aiSettingsForm = reactive({
  modelType: 'yolov8',
  confidenceThreshold: 75,
  realTimeInference: true,
  defectCategories: ['断经', '断纬', '色差', '污渍', '破损']
})

/**
 * 保存设置
 */
async function handleSave() {
  saving.value = true
  try {
    // TODO: 调用API保存设置
    // await saveSettings({ ...settingsForm, ...aiSettingsForm })
    
    // 模拟保存延迟
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('设置保存成功')
  } catch (error) {
    console.error('保存设置失败:', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

/**
 * 重置设置
 */
function handleReset() {
  // 重置为基础值
  settingsForm.systemName = 'FabricEye AI验布系统'
  settingsForm.autoInspection = true
  settingsForm.defectThreshold = 50
  settingsForm.videoRetentionDays = 7
  
  aiSettingsForm.modelType = 'yolov8'
  aiSettingsForm.confidenceThreshold = 75
  aiSettingsForm.realTimeInference = true
  aiSettingsForm.defectCategories = ['断经', '断纬', '色差', '污渍', '破损']
  
  ElMessage.info('已重置为默认值')
}
</script>

<style scoped>
.settings-view {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.settings-card {
  margin-bottom: 20px;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
}

.save-section {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.info-card {
  margin-bottom: 20px;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.info-item {
  display: flex;
  justify-content: space-between;
}

.info-item .label {
  color: #606266;
}

.info-item .value {
  color: #303133;
  font-weight: 500;
}

.about-card {
  margin-bottom: 20px;
}

.about-content {
  text-align: center;
  color: #606266;
  line-height: 1.8;
}

.about-content .copyright {
  margin-top: 20px;
  font-size: 12px;
  color: #909399;
}
</style>

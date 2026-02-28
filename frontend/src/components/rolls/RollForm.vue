<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑布卷' : '新建布卷'"
    width="600px"
    destroy-on-close
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
    >
      <el-form-item label="布卷号" prop="rollNumber">
        <el-input 
          v-model="formData.rollNumber" 
          placeholder="请输入布卷号" 
          :disabled="isEdit"
        />
      </el-form-item>
      
      <el-form-item label="面料类型" prop="fabricType">
        <el-select v-model="formData.fabricType" placeholder="请选择面料类型">
          <el-option label="棉布" value="cotton" />
          <el-option label="丝绸" value="silk" />
          <el-option label="涤纶" value="polyester" />
          <el-option label="麻布" value="linen" />
          <el-option label="羊毛" value="wool" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="面料颜色" prop="fabricColor">
        <el-input v-model="formData.fabricColor" placeholder="请输入面料颜色" />
      </el-form-item>
      
      <el-form-item label="长度(米)" prop="length">
        <el-input-number 
          v-model="formData.length" 
          :min="1" 
          :max="10000"
          controls-position="right"
        />
      </el-form-item>
      
      <el-form-item label="幅宽(厘米)" prop="width">
        <el-input-number 
          v-model="formData.width" 
          :min="1" 
          :max="500"
          controls-position="right"
        />
      </el-form-item>
      
      <el-form-item label="供应商" prop="supplier">
        <el-input v-model="formData.supplier" placeholder="请输入供应商名称" />
      </el-form-item>
      
      <el-form-item label="备注" prop="remark">
        <el-input
          v-model="formData.remark"
          type="textarea"
          :rows="3"
          placeholder="请输入备注信息"
        />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRollsStore } from '@/stores'
import { ElMessage } from 'element-plus'

// 定义props
const props = defineProps({
  // 控制对话框显示
  modelValue: {
    type: Boolean,
    default: false
  },
  // 布卷数据（编辑时传入）
  rollData: {
    type: Object,
    default: null
  }
})

// 定义emit
const emit = defineEmits(['update:modelValue', 'success'])

// 使用Store
const rollsStore = useRollsStore()

// 表单引用
const formRef = ref(null)

// 提交状态
const submitting = ref(false)

// 表单数据
const formData = ref({
  rollNumber: '',
  fabricType: '',
  fabricColor: '',
  length: 100,
  width: 150,
  supplier: '',
  remark: ''
})

// 表单验证规则
const formRules = {
  rollNumber: [
    { required: true, message: '请输入布卷号', trigger: 'blur' }
  ],
  fabricType: [
    { required: true, message: '请选择面料类型', trigger: 'change' }
  ],
  fabricColor: [
    { required: true, message: '请输入面料颜色', trigger: 'blur' }
  ],
  length: [
    { required: true, message: '请输入长度', trigger: 'blur' }
  ]
}

// 对话框显示状态
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 是否为编辑模式
const isEdit = computed(() => !!props.rollData)

/**
 * 监听rollData变化，回填表单
 */
watch(() => props.rollData, (newVal) => {
  if (newVal) {
    formData.value = { ...newVal }
  } else {
    // 重置表单
    formData.value = {
      rollNumber: '',
      fabricType: '',
      fabricColor: '',
      length: 100,
      width: 150,
      supplier: '',
      remark: ''
    }
  }
}, { immediate: true })

/**
 * 关闭对话框
 */
function handleClose() {
  dialogVisible.value = false
  formRef.value?.resetFields()
}

/**
 * 提交表单
 */
async function handleSubmit() {
  try {
    // 表单验证
    await formRef.value?.validate()
    
    submitting.value = true
    
    if (isEdit.value) {
      // 编辑布卷
      await rollsStore.updateRoll(props.rollData.id, formData.value)
      ElMessage.success('编辑成功')
    } else {
      // 创建布卷
      await rollsStore.createRoll(formData.value)
      ElMessage.success('创建成功')
    }
    
    // 触发成功事件
    emit('success')
    handleClose()
  } catch (error) {
    if (error !== false) {
      console.error('提交失败:', error)
      ElMessage.error('操作失败')
    }
  } finally {
    submitting.value = false
  }
}
</script>

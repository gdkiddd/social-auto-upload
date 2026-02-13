<template>
  <div class="history-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <el-icon><Clock /></el-icon>
          <span>上传历史记录</span>
        </div>
      </template>

      <el-table :data="history" style="width: 100%" v-loading="loading">
        <el-table-column prop="date" label="日期时间" width="180" />
        <el-table-column prop="account" label="账号" width="100" />
        <el-table-column prop="video" label="视频" min-width="200">
          <template #default="scope">
            <span>{{ scope.row.video.substring(0, 50) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="platforms" label="平台数" width="100" align="center" />
        <el-table-column prop="result" label="结果" width="100" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.result === 'success'" type="success" size="small">
              成功
            </el-tag>
            <el-tag v-else type="danger" size="small">
              失败
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const loading = ref(false)
const history = ref([])

const fetchHistory = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/history')
    if (response.data.code === 200) {
      history.value = response.data.data
    }
  } catch (error) {
    console.error('获取历史记录失败:', error)
    ElMessage.error('获取历史记录失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchHistory()
})
</script>

<style lang="scss" scoped>
.history-container {
  padding: 20px;

  .box-card {
    .card-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-weight: bold;
      font-size: 1.1rem;
    }
  }
}
</style>

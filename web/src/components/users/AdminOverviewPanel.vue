<template>
  <UserPanelCard title="管理概览">
    <template #actions>
      <mdui-button variant="filled" :disabled="!canAccess || isLoading" :loading="isLoading" @click="load">
        刷新
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>
    <div v-else-if="!canAccess" class="user-panel-empty-hint">仅管理员可查看。</div>

    <div v-else class="user-panel-stack">
      <div class="user-panel-summary-grid admin-overview-grid">
        <div class="user-panel-stat">
          <div class="user-panel-stat-label">用户总数</div>
          <div class="user-panel-stat-value">{{ formatNumber(overview?.total_users) }}</div>
          <div class="user-panel-stat-copy">当前系统账号数量。</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">活跃用户</div>
          <div class="user-panel-stat-value">{{ formatNumber(overview?.active_users) }}</div>
          <div class="user-panel-stat-copy">仍可正常登录的账号。</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">Paste 总数</div>
          <div class="user-panel-stat-value">{{ formatNumber(overview?.total_pastes) }}</div>
          <div class="user-panel-stat-copy">包含草稿、已发布和已编辑。</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">文件总量</div>
          <div class="user-panel-stat-value">{{ formatNumber(overview?.total_files) }}</div>
          <div class="user-panel-stat-copy">已完成上传并绑定 Paste 的文件。</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">存储占用</div>
          <div class="user-panel-stat-value">{{ humanSize(overview?.total_storage_bytes ?? 0) }}</div>
          <div class="user-panel-stat-copy">按附件原始大小汇总。</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">总访问量</div>
          <div class="user-panel-stat-value">{{ formatNumber(overview?.total_view_count) }}</div>
          <div class="user-panel-stat-copy">成功读取 Paste 内容累计次数。</div>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && !overview" class="user-panel-empty-state" role="status">
        <div class="user-panel-empty-state-icon" aria-hidden="true">
          <mdui-icon name="dashboard"></mdui-icon>
        </div>
        <div>
          <div class="user-panel-empty-state-title">暂时无法展示概览</div>
          <div class="user-panel-empty-state-copy">刷新后仍不可用时，请检查管理员接口或登录状态。</div>
        </div>
      </div>
    </div>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'

import { useAuth } from '../../composables/useAuth'
import { getAdminOverview, type AdminOverviewResponse } from '../../services/admin'
import { extractErrorMessage } from '../../utils/error'
import { humanSize } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

const { currentUser } = useAuth()

const overview = ref<AdminOverviewResponse | null>(null)
const isLoading = ref(false)

const canAccess = computed(() => currentUser.value?.role === 'admin')

function formatNumber(value: number | null | undefined): string {
  return Number(value ?? 0).toLocaleString()
}

async function load() {
  if (!canAccess.value) {
    overview.value = null
    return
  }

  isLoading.value = true
  try {
    overview.value = await getAdminOverview()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取管理概览失败'), closeable: true })
  } finally {
    isLoading.value = false
  }
}

watch(
  canAccess,
  () => {
    void load()
  },
  { immediate: true }
)
</script>

<style scoped>
.admin-overview-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

@media (max-width: 960px) {
  .admin-overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>

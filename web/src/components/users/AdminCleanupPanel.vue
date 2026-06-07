<template>
  <UserPanelCard title="清理任务">
    <template #actions>
      <mdui-button variant="tonal" :disabled="!canAccess || isLoading || isRunning" :loading="isLoading" @click="load">
        刷新
      </mdui-button>
      <mdui-button
        variant="filled"
        :disabled="!canRunSelected"
        :loading="isRunningSelected"
        @click="runSelected"
      >
        执行已选择
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>
    <div v-else-if="!canAccess" class="user-panel-empty-hint">仅管理员可查看。</div>

    <div v-else class="user-panel-stack">
      <div class="user-panel-section user-panel-section--soft">
        <div class="user-panel-section-header">
          <div class="user-panel-section-heading">
            <div class="user-panel-section-eyebrow">Maintenance</div>
            <div class="user-panel-section-title">待清理任务</div>
            <div class="user-panel-section-copy">
              当前共有 {{ formatNumber(totalPending) }} 条记录可清理；可单独执行，也可选择多个任务批量执行。
            </div>
          </div>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading || isRunning"></mdui-linear-progress>

      <div v-if="!isLoading && tasks.length === 0" class="user-panel-empty-state" role="status">
        <div class="user-panel-empty-state-icon" aria-hidden="true">
          <mdui-icon name="cleaning_services"></mdui-icon>
        </div>
        <div>
          <div class="user-panel-empty-state-title">没有可用的清理任务</div>
          <div class="user-panel-empty-state-copy">刷新后仍为空时，请检查管理员清理接口。</div>
        </div>
      </div>

      <div v-else class="user-panel-row-list">
        <article v-for="task in tasks" :key="task" class="user-panel-row cleanup-row">
          <div class="user-panel-row-main">
            <div class="user-panel-row-title-row">
              <button
                class="cleanup-select"
                type="button"
                :aria-pressed="isSelected(task)"
                :aria-label="`${isSelected(task) ? '取消选择' : '选择'}${taskMeta(task).label}`"
                :disabled="isTaskRunning(task)"
                @click="toggleTask(task)"
              >
                <mdui-icon :name="isSelected(task) ? 'check' : 'add'"></mdui-icon>
              </button>
              <div class="admin-task-icon" aria-hidden="true">
                <mdui-icon :name="taskMeta(task).icon"></mdui-icon>
              </div>
              <div class="user-panel-row-title">{{ taskMeta(task).label }}</div>
              <mdui-chip :variant="cleanupCount(task) > 0 ? 'filled' : 'outlined'">
                {{ cleanupCount(task) }} 条
              </mdui-chip>
            </div>

            <div class="user-panel-row-description">{{ taskMeta(task).description }}</div>

            <div v-if="resultFor(task)" class="cleanup-result" :class="{ 'cleanup-result--error': !resultFor(task)?.success }">
              {{ resultFor(task)?.message }}
              <span v-if="resultFor(task)?.error">：{{ resultFor(task)?.error }}</span>
            </div>
          </div>

          <div class="user-panel-row-actions">
            <mdui-button
              variant="text"
              :disabled="isTaskRunning(task)"
              :loading="isTaskRunning(task)"
              @click="runSingle(task)"
            >
              执行
            </mdui-button>
          </div>
        </article>
      </div>

      <div v-if="lastResponse" class="user-panel-section">
        <div class="user-panel-section-header">
          <div class="user-panel-section-heading">
            <div class="user-panel-section-eyebrow">Result</div>
            <div class="user-panel-section-title">{{ lastResponse.success ? '清理完成' : '清理部分失败' }}</div>
            <div class="user-panel-section-copy">
              {{ lastResponse.message }}；总计删除 {{ formatNumber(lastResponse.total_deleted) }} 条记录。
            </div>
          </div>
        </div>
      </div>
    </div>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/chip.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'

import { useAuth } from '../../composables/useAuth'
import {
  executeAdminCleanup,
  getAdminCleanupStatus,
  type AdminCleanupStatusResponse,
  type CleanupResponse,
  type CleanupTaskName,
  type CleanupTaskResult
} from '../../services/admin'
import { extractErrorMessage } from '../../utils/error'
import UserPanelCard from './UserPanelCard.vue'
import { CLEANUP_TASK_META, sortedCleanupTasks } from './adminTasks'
import './panel.css'

const { currentUser } = useAuth()

const status = ref<AdminCleanupStatusResponse | null>(null)
const selectedTasks = ref<CleanupTaskName[]>([])
const lastResponse = ref<CleanupResponse | null>(null)
const isLoading = ref(false)
const runningTask = ref<CleanupTaskName | 'selected' | null>(null)

const canAccess = computed(() => currentUser.value?.role === 'admin')
const tasks = computed(() => sortedCleanupTasks(status.value?.supported_tasks ?? []))
const isRunning = computed(() => runningTask.value !== null)
const isRunningSelected = computed(() => runningTask.value === 'selected')
const canRunSelected = computed(() => canAccess.value && selectedTasks.value.length > 0 && !isRunning.value)
const totalPending = computed(() => tasks.value.reduce((sum, task) => sum + cleanupCount(task), 0))

function formatNumber(value: number | null | undefined): string {
  return Number(value ?? 0).toLocaleString()
}

function cleanupCount(task: CleanupTaskName): number {
  return status.value?.cleanup_counts[task] ?? 0
}

function taskMeta(task: CleanupTaskName) {
  return CLEANUP_TASK_META[task]
}

function isSelected(task: CleanupTaskName): boolean {
  return selectedTasks.value.includes(task)
}

function isTaskRunning(task: CleanupTaskName): boolean {
  return runningTask.value === task || runningTask.value === 'selected'
}

function toggleTask(task: CleanupTaskName) {
  if (isTaskRunning(task)) return
  if (isSelected(task)) {
    selectedTasks.value = selectedTasks.value.filter((item) => item !== task)
    return
  }
  selectedTasks.value = [...selectedTasks.value, task]
}

function resultFor(task: CleanupTaskName): CleanupTaskResult | undefined {
  return lastResponse.value?.task_results.find((result) => result.task_name === task)
}

function cleanupConfirmationText(tasksToRun: CleanupTaskName[]): string {
  const taskText = tasksToRun
    .map((task) => `${taskMeta(task).label}（${formatNumber(cleanupCount(task))} 条）`)
    .join('、')

  if (tasksToRun.length === 1) {
    return `将执行 ${taskText} 清理。该操作会删除匹配记录，确认继续？`
  }

  return `将执行 ${tasksToRun.length} 个清理任务：${taskText}。该操作会删除匹配记录，确认继续？`
}

async function load() {
  if (!canAccess.value) {
    status.value = null
    selectedTasks.value = []
    return
  }

  isLoading.value = true
  try {
    status.value = await getAdminCleanupStatus()
    selectedTasks.value = selectedTasks.value.filter((task) => status.value?.supported_tasks.includes(task))
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取清理任务失败'), closeable: true })
  } finally {
    isLoading.value = false
  }
}

async function execute(tasksToRun: CleanupTaskName[], running: CleanupTaskName | 'selected') {
  if (!canAccess.value || tasksToRun.length === 0 || isRunning.value) return

  const firstTask = tasksToRun[0]
  if (!firstTask) return

  try {
    await confirm({
      headline: running === 'selected' ? '执行已选择的清理任务' : `执行${taskMeta(firstTask).label}`,
      description: cleanupConfirmationText(tasksToRun),
      confirmText: '执行',
      cancelText: '取消',
      closeOnEsc: true,
      closeOnOverlayClick: true
    })
  } catch {
    return
  }

  runningTask.value = running
  try {
    lastResponse.value = await executeAdminCleanup(tasksToRun)
    snackbar({ message: lastResponse.value.message, closeable: true })
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '执行清理任务失败'), closeable: true })
  } finally {
    runningTask.value = null
  }
}

function runSingle(task: CleanupTaskName) {
  void execute([task], task)
}

function runSelected() {
  void execute([...selectedTasks.value], 'selected')
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
.admin-task-icon,
.cleanup-select {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 12px;
}

.admin-task-icon {
  background: rgb(var(--mdui-color-surface-container-high));
  color: rgb(var(--mdui-color-on-surface-variant));
}

.cleanup-select {
  padding: 0;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.75);
  background: rgb(var(--mdui-color-surface));
  color: rgb(var(--mdui-color-on-surface-variant));
  cursor: pointer;
}

.cleanup-select[aria-pressed='true'] {
  border-color: rgb(var(--mdui-color-primary));
  background: rgb(var(--mdui-color-primary-container));
  color: rgb(var(--mdui-color-on-primary-container));
}

.cleanup-select:disabled {
  cursor: default;
  opacity: 0.55;
}

.cleanup-result {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgb(var(--mdui-color-surface-container-high));
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 0.86rem;
  line-height: 1.5;
}

.cleanup-result--error {
  background: rgb(var(--mdui-color-error-container));
  color: rgb(var(--mdui-color-on-error-container));
}
</style>

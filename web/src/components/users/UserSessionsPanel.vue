<template>
  <UserPanelCard title="会话管理">
    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>

    <div v-else class="user-panel-stack">
      <div class="user-panel-summary-grid">
        <div class="user-panel-stat">
          <div class="user-panel-stat-label">当前设备</div>
          <div class="user-panel-stat-value">{{ currentSessionCount }}</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">其他会话</div>
          <div class="user-panel-stat-value">{{ otherSessionCount }}</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">全部会话</div>
          <div class="user-panel-stat-value">{{ sessions.length }}</div>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && pagedSessions.length === 0" class="user-panel-empty-hint">暂无会话。</div>

      <div v-else class="user-panel-row-list">
        <article v-for="session in pagedSessions" :key="session.id" class="user-panel-row">
          <div class="user-panel-row-main">
            <div class="user-panel-row-title-row">
              <div class="user-panel-row-title">{{ sessionHeadline(session) }}</div>
              <code class="session-id">{{ shortId(session.id) }}</code>
              <mdui-chip :variant="session.is_current ? 'filled' : 'outlined'">
                {{ session.is_current ? '当前设备' : '历史会话' }}
              </mdui-chip>
            </div>

            <div class="user-panel-meta">
              <span class="user-panel-meta-item">IP {{ session.ip_address ?? '-' }}</span>
              <span class="user-panel-meta-item">登录于 {{ formatDate(session.created_at) }}</span>
              <span class="user-panel-meta-item">最后活跃 {{ formatDate(session.last_active_at) }}</span>
              <span class="user-panel-meta-item">将于 {{ formatDate(session.expires_at) }} 自动登出</span>
            </div>
          </div>

          <div class="user-panel-row-actions">
            <mdui-button
              variant="text"
              :disabled="isRevokingId === session.id"
              :loading="isRevokingId === session.id"
              @click="revoke(session.id, session.is_current)"
            >
              {{ session.is_current ? '登出' : '撤销会话' }}
            </mdui-button>
          </div>
        </article>
      </div>

      <div class="user-panel-toolbar session-toolbar">
        <mdui-button
          variant="filled"
          :disabled="!currentUser || !hasOtherSessions || isRevokingOthers"
          :loading="isRevokingOthers"
          @click="revokeOthers"
        >
          撤销其他会话
        </mdui-button>
        <mdui-button
          v-if="isAdmin"
          variant="text"
          :disabled="isCleaning"
          :loading="isCleaning"
          @click="cleanup"
        >
          清理过期会话
        </mdui-button>
      </div>

      <PaginationFooter
        v-if="sessions.length > 0"
        :total="sessions.length"
        :page="page"
        :total-pages="totalPages"
        :loading="isLoading"
        @change-page="handlePageChange"
      />
    </div>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/chip.js'
import 'mdui/components/linear-progress.js'

import PaginationFooter from '../common/PaginationFooter.vue'
import { useAuth } from '../../composables/useAuth'
import {
  cleanupExpiredSessions,
  getUserSessions,
  revokeOtherSessions,
  revokeSession,
  type SessionResponse
} from '../../services/user'
import { getDeviceLabel } from '../../utils/device'
import { extractErrorMessage } from '../../utils/error'
import { formatDate } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

const PAGE_SIZE = 8

const { currentUser } = useAuth()

const sessions = ref<SessionResponse[]>([])
const isLoading = ref(false)
const isCleaning = ref(false)
const isRevokingOthers = ref(false)
const isRevokingId = ref<string | null>(null)
const page = ref(1)

const sortedSessions = computed(() => [...sessions.value].sort((a, b) => Number(b.is_current) - Number(a.is_current)))
const hasOtherSessions = computed(() => sessions.value.some((session) => !session.is_current))
const isAdmin = computed(() => currentUser.value?.role === 'admin')
const currentSessionCount = computed(() => sessions.value.filter((session) => session.is_current).length)
const otherSessionCount = computed(() => sessions.value.filter((session) => !session.is_current).length)
const totalPages = computed(() => Math.max(1, Math.ceil(sortedSessions.value.length / PAGE_SIZE)))
const pagedSessions = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return sortedSessions.value.slice(start, start + PAGE_SIZE)
})

watch(totalPages, (nextTotalPages) => {
  if (page.value > nextTotalPages) {
    page.value = nextTotalPages
  }
})

function handlePageChange(nextPage: number) {
  page.value = nextPage
}

function shortId(id: string): string {
  if (id.length <= 12) return id
  return `${id.slice(0, 6)}...${id.slice(-4)}`
}

function sessionHeadline(session: SessionResponse): string {
  return getDeviceLabel(session.user_agent)
}

async function loadSessions() {
  if (!currentUser.value) return
  isLoading.value = true
  try {
    sessions.value = await getUserSessions(currentUser.value.id)
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取会话失败'), closeable: true })
  } finally {
    isLoading.value = false
  }
}

async function revoke(sessionId: string, isCurrent: boolean) {
  try {
    await confirm({
      headline: '撤销会话',
      description: isCurrent
        ? '确认撤销当前会话？你将需要重新登录。'
        : '确认撤销该会话？撤销后该设备将需要重新登录。',
      confirmText: '撤销',
      cancelText: '取消',
      closeOnEsc: true,
      closeOnOverlayClick: true
    })
  } catch {
    return
  }

  isRevokingId.value = sessionId
  try {
    await revokeSession(sessionId)
    snackbar({ message: '会话已撤销' })
    await loadSessions()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '撤销失败'), closeable: true })
  } finally {
    isRevokingId.value = null
  }
}

async function revokeOthers() {
  if (!currentUser.value) return

  try {
    await confirm({
      headline: '撤销其他会话',
      description: '将保留当前设备登录，其他设备全部退出。是否继续？',
      confirmText: '撤销',
      cancelText: '取消',
      closeOnEsc: true,
      closeOnOverlayClick: true
    })
  } catch {
    return
  }

  isRevokingOthers.value = true
  try {
    const resp = await revokeOtherSessions(currentUser.value.id)
    snackbar({ message: resp.message })
    await loadSessions()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '批量撤销失败'), closeable: true })
  } finally {
    isRevokingOthers.value = false
  }
}

async function cleanup() {
  isCleaning.value = true
  try {
    const resp = await cleanupExpiredSessions()
    snackbar({ message: resp.message })
    await loadSessions()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '清理失败'), closeable: true })
  } finally {
    isCleaning.value = false
  }
}

onMounted(() => {
  void loadSessions()
})
</script>

<style scoped>
.session-id {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgb(var(--mdui-color-surface-container-high));
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.82rem;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.session-toolbar {
  justify-content: flex-start;
}
</style>

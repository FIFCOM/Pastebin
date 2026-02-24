<template>
  <UserPanelCard title="会话管理" subtitle="查看当前设备与历史会话并执行撤销">
    <template #actions>
      <mdui-button
        variant="tonal"
        :disabled="!currentUser || isLoading"
        :loading="isLoading"
        @click="loadSessions"
      >
        刷新
      </mdui-button>
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
        :disabled="!currentUser || isCleaning"
        :loading="isCleaning"
        @click="cleanup"
      >
        清理过期会话
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录</div>

    <div v-else>
      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && sessions.length === 0" class="user-panel-empty-hint">
        暂无会话
      </div>

      <mdui-list v-else class="user-panel-list">
        <mdui-list-item
          v-for="s in sessions"
          :key="s.id"
          :headline="sessionHeadline(s)"
          :description="sessionDescription(s)"
          description-line="3"
          rounded
        >
          <div slot="end-icon" class="session-actions">
            <mdui-chip v-if="s.is_current" variant="filled">当前</mdui-chip>
            <mdui-button-icon
              :disabled="isRevokingId === s.id"
              :loading="isRevokingId === s.id"
              @click.stop="revoke(s.id, s.is_current)"
            >
              <mdui-icon name="delete"></mdui-icon>
            </mdui-button-icon>
          </div>
        </mdui-list-item>
      </mdui-list>
    </div>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/chip.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'

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
import { formatDateTime } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

const { currentUser } = useAuth()

const sessions = ref<SessionResponse[]>([])
const isLoading = ref(false)
const isCleaning = ref(false)
const isRevokingOthers = ref(false)
const isRevokingId = ref<string | null>(null)

const hasOtherSessions = computed(() => sessions.value.some((session) => !session.is_current))
const isAdmin = computed(() => currentUser.value?.role === 'admin')

function shortId(id: string): string {
  if (id.length <= 12) return id
  return `${id.slice(0, 6)}...${id.slice(-4)}`
}

function sessionHeadline(session: SessionResponse): string {
  return getDeviceLabel(session.user_agent)
}

function sessionDescription(session: SessionResponse): string {
  const parts = [
    `IP ${session.ip_address ?? '-'}`,
    `最后活跃 ${formatDateTime(session.last_active_at)}`,
    `创建 ${formatDateTime(session.created_at)}`,
    `过期 ${formatDateTime(session.expires_at)}`,
    `会话 ${shortId(session.id)}`
  ]

  return parts.join(' · ')
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
.session-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

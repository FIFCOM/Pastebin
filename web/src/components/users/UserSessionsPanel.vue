<template>
  <mdui-card class="panel-card">
    <div class="panel-header">
      <div>
        <div class="panel-title">会话管理</div>
        <div class="panel-subtitle">查看并撤销已登录的会话</div>
      </div>

      <div class="header-actions">
        <mdui-button
          variant="tonal"
          :disabled="!currentUser || isLoading"
          :loading="isLoading"
          @click="loadSessions"
        >
          刷新
        </mdui-button>
        <mdui-button
          variant="text"
          :disabled="!currentUser || isCleaning"
          :loading="isCleaning"
          @click="cleanup"
        >
          清理过期会话
        </mdui-button>
      </div>
    </div>

    <mdui-divider></mdui-divider>

    <div v-if="!currentUser" class="empty-hint">请先登录</div>

    <div v-else>
      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && sessions.length === 0" class="empty-hint">
        暂无会话
      </div>

      <mdui-list v-else class="session-list">
        <mdui-list-item
          v-for="s in sessions"
          :key="s.id"
          :headline="formatDate(s.created_at)"
          :description="`过期时间：${formatDate(s.expires_at)}\\nID：${shortId(s.id)}`"
          description-line="2"
          rounded
        >
          <div slot="end-icon" class="end-actions">
            <mdui-button-icon
              :disabled="isRevokingId === s.id"
              :loading="isRevokingId === s.id"
              @click.stop="revoke(s.id)"
            >
              <mdui-icon name="delete"></mdui-icon>
            </mdui-button-icon>
          </div>
        </mdui-list-item>
      </mdui-list>
    </div>
  </mdui-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import { confirm } from 'mdui/functions/confirm.js'
import 'mdui/components/card.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/divider.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'

import { useAuth } from '../../composables/useAuth'
import { cleanupExpiredSessions, getUserSessions, revokeSession } from '../../services/user'
import type { SessionResponse } from '../../services/user'

const { currentUser } = useAuth()

const sessions = ref<SessionResponse[]>([])
const isLoading = ref(false)
const isCleaning = ref(false)
const isRevokingId = ref<string | null>(null)

function formatDate(raw: string): string {
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleString()
}

function shortId(id: string): string {
  if (id.length <= 12) return id
  return `${id.slice(0, 6)}…${id.slice(-4)}`
}

async function loadSessions() {
  if (!currentUser.value) return
  isLoading.value = true
  try {
    sessions.value = await getUserSessions(currentUser.value.id)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '获取会话失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isLoading.value = false
  }
}

async function revoke(sessionId: string) {
  try {
    await confirm({
      headline: '撤销会话',
      description: '确认撤销该会话？撤销后该设备将需要重新登录。',
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
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    snackbar({ message: '会话已撤销' })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '撤销失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isRevokingId.value = null
  }
}

async function cleanup() {
  isCleaning.value = true
  try {
    const resp = await cleanupExpiredSessions()
    snackbar({ message: resp.message })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '清理失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isCleaning.value = false
  }
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
.panel-card {
  padding: 20px;
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.2;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.empty-hint {
  margin: 16px 0 0;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.session-list {
  margin-top: 8px;
}

.end-actions {
  display: flex;
  align-items: center;
}
</style>

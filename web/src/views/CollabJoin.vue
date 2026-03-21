<template>
  <div class="join-page">
    <section class="join-shell">
      <div class="join-header surface-card">
        <p class="join-kicker">邀请确认</p>
        <h1>加入协作房间</h1>
        <p class="join-description">
          先确认邀请码对应的房间，再以当前成员身份加入。加入成功后，房间密钥与实时连接地址只保存在当前标签页的会话存储里。
        </p>
      </div>

      <section class="surface-card room-overview" :aria-busy="isLoadingRoomInfo ? 'true' : 'false'">
        <div v-if="isLoadingRoomInfo" class="state-block" role="status">
          <mdui-circular-progress></mdui-circular-progress>
          <span>正在确认邀请码…</span>
        </div>

        <div v-else-if="roomInfo" class="room-summary">
          <div>
            <p class="summary-label">房间名称</p>
            <h2>{{ roomInfo.room_name }}</h2>
          </div>

          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-value">{{ pinCode }}</span>
              <span class="summary-caption">邀请码</span>
            </div>
            <div class="summary-item">
              <span class="summary-value">{{ roomInfo.member_count }}</span>
              <span class="summary-caption">当前成员</span>
            </div>
            <div class="summary-item">
              <span class="summary-value">{{ roomInfo.max_members }}</span>
              <span class="summary-caption">成员上限</span>
            </div>
          </div>

          <div class="identity-inline">
            <span class="summary-caption">将以 {{ memberIdentity?.displayName || '新的访客身份' }} 加入</span>
            <mdui-button variant="text" :loading="isEnsuringMemberIdentity" @click="handleRefreshIdentity">
              更新身份
            </mdui-button>
          </div>

          <div class="join-actions">
            <mdui-button variant="text" @click="handleBackToLobby">返回首页</mdui-button>
            <mdui-button variant="filled" :loading="isJoining" @click="handleJoinRoom">
              加入并进入工作区
            </mdui-button>
          </div>
        </div>

        <div v-else class="state-block error-block" role="alert">
          <mdui-icon name="error_outline"></mdui-icon>
          <span>{{ roomInfoError || '邀请码无效或房间已关闭' }}</span>
          <mdui-button variant="tonal" @click="handleBackToLobby">返回首页</mdui-button>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import 'mdui/components/button.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/icon.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import { useRoomSession } from '../composables/useRoomSession'
import { getRoomInfoByPin, type RoomInfoResponse } from '../services/rooms'

const route = useRoute()
const router = useRouter()
const { memberIdentity, isEnsuringMemberIdentity, ensureMemberIdentity, joinExistingRoom } = useRoomSession()

const roomInfo = ref<RoomInfoResponse | null>(null)
const roomInfoError = ref('')
const isLoadingRoomInfo = ref(false)
const isJoining = ref(false)

const pinCode = computed(() => String(route.params.pin || '').trim().toUpperCase())

async function loadRoomInfo(): Promise<void> {
  if (!/^[A-Z0-9]{6}$/.test(pinCode.value)) {
    roomInfoError.value = '邀请码格式无效'
    roomInfo.value = null
    return
  }

  isLoadingRoomInfo.value = true
  roomInfoError.value = ''
  try {
    roomInfo.value = await getRoomInfoByPin(pinCode.value)
  } catch (error) {
    roomInfo.value = null
    roomInfoError.value = error instanceof Error ? error.message : '邀请码无效或房间已关闭'
  } finally {
    isLoadingRoomInfo.value = false
  }
}

async function handleRefreshIdentity(): Promise<void> {
  try {
    const identity = await ensureMemberIdentity(true)
    snackbar({ message: `将以 ${identity.displayName} 加入` })
  } catch (error) {
    snackbar({
      message: error instanceof Error ? error.message : '获取成员身份失败',
      closeable: true
    })
  }
}

async function handleJoinRoom(): Promise<void> {
  if (!roomInfo.value) return

  isJoining.value = true
  try {
    const session = await joinExistingRoom({
      roomId: roomInfo.value.room_id,
      roomName: roomInfo.value.room_name,
      pinCode: pinCode.value,
      joinUrl: `/join/${pinCode.value}`,
      memberCount: Math.min(roomInfo.value.member_count + 1, roomInfo.value.max_members),
      maxMembers: roomInfo.value.max_members
    })
    await router.push(`/rooms/${session.roomId}`)
  } catch (error) {
    snackbar({
      message: error instanceof Error ? error.message : '加入房间失败',
      closeable: true
    })
  } finally {
    isJoining.value = false
  }
}

async function handleBackToLobby(): Promise<void> {
  await router.push('/')
}

onMounted(() => {
  void ensureMemberIdentity().catch((error: unknown) => {
    snackbar({
      message: error instanceof Error ? error.message : '预取成员身份失败，请在加入前重试',
      closeable: true
    })
  })
  void loadRoomInfo()
})

watch(pinCode, () => {
  void loadRoomInfo()
})
</script>

<style scoped>
.join-page {
  padding: 24px 0 32px;
}

.join-shell {
  max-width: 780px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.surface-card {
  padding: 22px;
  border-radius: 26px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.72);
  background: rgb(var(--mdui-color-surface));
}

.join-header {
  background:
    linear-gradient(140deg, rgb(var(--mdui-color-primary-container) / 0.44), transparent 42%),
    rgb(var(--mdui-color-surface-container-low));
}

.join-kicker,
.summary-label {
  margin: 0;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-weight: 700;
  color: rgb(var(--mdui-color-primary));
}

.join-header h1,
.room-summary h2 {
  margin: 10px 0 8px;
}

.join-description {
  margin: 0;
  color: rgb(var(--mdui-color-on-surface-variant));
  line-height: 1.7;
}

.state-block {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  text-align: center;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.room-summary {
  display: grid;
  gap: 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-item {
  display: grid;
  gap: 6px;
  padding: 16px;
  border-radius: 18px;
  background: rgb(var(--mdui-color-surface-container-low));
}

.summary-value {
  font-size: 1.3rem;
  font-weight: 700;
}

.summary-caption {
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 0.86rem;
}

.identity-inline,
.join-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.error-block mdui-icon {
  font-size: 34px;
}

@media (max-width: 640px) {
  .join-page {
    padding-top: 18px;
  }

  .surface-card {
    padding: 18px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .join-actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }
}
</style>

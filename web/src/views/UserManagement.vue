<template>
  <div class="user-management">
    <div class="workspace-panel">
      <div class="content-panel">
        <KeepAlive>
          <component :is="activeComponent" />
        </KeepAlive>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '../composables/useAuth'
import AdminCleanupPanel from '../components/users/AdminCleanupPanel.vue'
import AdminOverviewPanel from '../components/users/AdminOverviewPanel.vue'
import AdminPastesPanel from '../components/users/AdminPastesPanel.vue'
import AdminSettingsPanel from '../components/users/AdminSettingsPanel.vue'
import AdminUsersListPanel from '../components/users/AdminUsersListPanel.vue'
import UserApiKeysPanel from '../components/users/UserApiKeysPanel.vue'
import UserProfilePanel from '../components/users/UserProfilePanel.vue'
import UserSessionsPanel from '../components/users/UserSessionsPanel.vue'
import UserTotpPanel from '../components/users/UserTotpPanel.vue'
import {
  normalizeUserTab,
  type UserTabValue
} from '../components/users/navigation'
import { registerHeaderActions, unregisterHeaderActions } from '../composables/useHeaderActions'

const router = useRouter()
const route = useRoute()
const { currentUser, isAuthInitialized } = useAuth()
const HEADER_OWNER_ID = 'user-management-page'

const isAdmin = computed(() => currentUser.value?.role === 'admin')
const activeTab = ref<UserTabValue>('profile')

const activeComponentMap: Record<UserTabValue, Component> = {
  profile: UserProfilePanel,
  sessions: UserSessionsPanel,
  totp: UserTotpPanel,
  apikeys: UserApiKeysPanel,
  'admin-overview': AdminOverviewPanel,
  'admin-users': AdminUsersListPanel,
  'admin-pastes': AdminPastesPanel,
  'admin-settings': AdminSettingsPanel,
  'admin-cleanup': AdminCleanupPanel
}

const activeComponent = computed(() => activeComponentMap[activeTab.value])

function updateRouteTab(tab: UserTabValue) {
  const current = typeof route.query.tab === 'string' ? route.query.tab : ''
  if (current === tab) return

  void router.replace({
    query: {
      ...route.query,
      tab
    }
  })
}

watch(
  [() => route.query.tab, isAdmin, isAuthInitialized],
  ([tab]) => {
    const normalized = normalizeUserTab(tab, isAdmin.value && isAuthInitialized.value)

    if (activeTab.value !== normalized) {
      activeTab.value = normalized
    }

    if (tab !== normalized) {
      updateRouteTab(normalized)
    }
  },
  { immediate: true }
)

onMounted(() => {
  registerHeaderActions(HEADER_OWNER_ID, [
    {
      id: 'users-new-paste',
      label: '新建 Paste',
      ariaLabel: '新建 Paste',
      icon: 'add',
      kind: 'icon',
      onClick: () => { void router.push('/') }
    },
    {
      id: 'users-history',
      label: '历史记录',
      ariaLabel: '查看历史记录',
      icon: 'history',
      kind: 'icon',
      onClick: () => { void router.push('/history') }
    },
    {
      id: 'users-favorites',
      label: '收藏',
      ariaLabel: '查看收藏',
      icon: 'star',
      kind: 'icon',
      onClick: () => { void router.push('/favorites') }
    }
  ])
})

onBeforeUnmount(() => {
  unregisterHeaderActions(HEADER_OWNER_ID)
})
</script>

<style scoped>
.user-management {
  padding: 18px 0 28px;
}

.workspace-panel {
  margin-top: 20px;
}

.content-panel {
  padding: 28px;
  border-radius: 30px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.68);
  background: rgb(var(--mdui-color-surface));
}

@media (max-width: 960px) {
  .content-panel {
    padding: 20px;
    border-radius: 24px;
  }
}

@media (max-width: 640px) {
.user-management {
    padding: 12px 0 24px;
  }

  .content-panel {
    padding: 16px;
  }
}
</style>

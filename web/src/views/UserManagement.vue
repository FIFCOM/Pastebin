<template>
  <div class="user-management">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <p class="page-subtitle">账户信息、会话、安全设置与 API Keys</p>
    </div>

    <mdui-tabs
      class="tabs"
      variant="secondary"
      full-width
      :value="activeTab"
      @change="handleTabChange"
    >
      <mdui-tab value="profile">我的账户</mdui-tab>
      <mdui-tab value="sessions">会话</mdui-tab>
      <mdui-tab value="totp">两步验证</mdui-tab>
      <mdui-tab value="apikeys">API Keys</mdui-tab>
      <mdui-tab value="users">用户列表</mdui-tab>

      <mdui-tab-panel slot="panel" value="profile">
        <UserProfilePanel />
      </mdui-tab-panel>
      <mdui-tab-panel slot="panel" value="sessions">
        <UserSessionsPanel />
      </mdui-tab-panel>
      <mdui-tab-panel slot="panel" value="totp">
        <UserTotpPanel />
      </mdui-tab-panel>
      <mdui-tab-panel slot="panel" value="apikeys">
        <UserApiKeysPanel />
      </mdui-tab-panel>
      <mdui-tab-panel slot="panel" value="users">
        <UserListPanel />
      </mdui-tab-panel>
    </mdui-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import 'mdui/components/tab.js'
import 'mdui/components/tab-panel.js'
import 'mdui/components/tabs.js'

import UserApiKeysPanel from '../components/users/UserApiKeysPanel.vue'
import UserListPanel from '../components/users/UserListPanel.vue'
import UserProfilePanel from '../components/users/UserProfilePanel.vue'
import UserSessionsPanel from '../components/users/UserSessionsPanel.vue'
import UserTotpPanel from '../components/users/UserTotpPanel.vue'

const TAB_VALUES = ['profile', 'sessions', 'totp', 'apikeys', 'users'] as const
type TabValue = (typeof TAB_VALUES)[number]

const activeTab = ref<TabValue>('profile')

function isTabValue(value: unknown): value is TabValue {
  return typeof value === 'string' && (TAB_VALUES as readonly string[]).includes(value)
}

function handleTabChange(e: Event) {
  const target = e.target as { value?: unknown } | null
  const value = target?.value
  if (isTabValue(value)) {
    activeTab.value = value
  }
}
</script>

<style scoped>
.user-management {
  padding: 16px 0;
}

.page-header {
  margin: 8px 0 16px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.tabs {
  width: 100%;
}

:deep(mdui-tab-panel[active]) {
  padding-top: 16px;
}
</style>

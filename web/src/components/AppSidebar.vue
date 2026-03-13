<template>
  <mdui-navigation-drawer
    class="app-sidebar"
    close-on-esc
    close-on-overlay-click
    :open="isAppSidebarOpen"
    @closed.self="closeAppSidebar"
    @opened.self="openAppSidebar"
  >
    <div class="sidebar-shell">
      <mdui-list class="sidebar-nav">
        <mdui-collapse ref="sidebarCollapseRef" class="sidebar-collapse" @change="syncExpandedSections">
          <mdui-collapse-item
            v-for="section in sidebarSections"
            :key="section.value"
            :value="section.value"
            class="sidebar-section"
          >
            <mdui-list-item
              slot="header"
              class="sidebar-group-header"
              rounded
              alignment="center"
              :icon="section.icon"
            >
              <span class="sidebar-group-label">{{ section.label }}</span>
              <mdui-icon
                slot="end-icon"
                :class="['sidebar-group-chevron', { 'sidebar-group-chevron--expanded': isSectionExpanded(section.value) }]"
                name="expand_more"
              ></mdui-icon>
            </mdui-list-item>

            <div class="sidebar-group-body">
              <mdui-list-item
                v-for="item in section.items"
                :key="item.key"
                class="sidebar-list-item"
                rounded
                alignment="center"
                :active="item.active ?? false"
                :disabled="item.disabled ?? false"
                :headline="item.label"
                :description="item.description"
                :icon="item.icon"
                @click="handleSidebarItemClick(item)"
              ></mdui-list-item>
            </div>
          </mdui-collapse-item>
        </mdui-collapse>
      </mdui-list>
    </div>
  </mdui-navigation-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Collapse } from 'mdui/components/collapse.js'
import 'mdui/components/collapse.js'
import 'mdui/components/collapse-item.js'
import 'mdui/components/icon.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'

import { useAuth } from '../composables/useAuth'
import { useAppSidebarState } from '../composables/useAppSidebarState'
import { getUserNavigationGroups, normalizeUserTab, type UserTabValue } from './users/navigation'

type SidebarSectionItem = {
  key: string
  label: string
  icon: string
  description?: string
  disabled?: boolean
  active?: boolean
  tab?: UserTabValue
}

type SidebarSection = {
  value: string
  label: string
  icon: string
  items: SidebarSectionItem[]
}

const DEFAULT_SECTIONS: SidebarSection[] = [
  {
    value: 'docs',
    label: '文档',
    icon: 'description',
    items: [
      {
        key: 'api-docs',
        label: 'API文档',
        icon: 'article',
        description: '占位入口，暂不实现跳转',
        disabled: true
      }
    ]
  },
  {
    value: 'about',
    label: '关于',
    icon: 'info',
    items: [
      {
        key: 'privacy-policy',
        label: '隐私政策',
        icon: 'policy',
        description: '占位入口，暂不实现跳转',
        disabled: true
      },
      {
        key: 'about-material-bin',
        label: '关于Material Bin',
        icon: 'info',
        description: '占位入口，暂不实现跳转',
        disabled: true
      }
    ]
  }
]

const route = useRoute()
const router = useRouter()
const { currentUser } = useAuth()
const { isAppSidebarOpen, openAppSidebar, closeAppSidebar } = useAppSidebarState()
const sidebarCollapseRef = ref<Collapse | null>(null)

const isUsersRoute = computed(() => route.path === '/users')
const canAccessUsers = computed(() => currentUser.value?.role === 'admin')
const userNavigationGroups = computed(() => getUserNavigationGroups(canAccessUsers.value))
const activeUserTab = computed(() => normalizeUserTab(route.query.tab, canAccessUsers.value))
const expandedSections = ref<string[]>([])

const sidebarSections = computed<SidebarSection[]>(() => {
  if (!isUsersRoute.value) {
    return DEFAULT_SECTIONS
  }

  return userNavigationGroups.value.map((group) => ({
    value: `users-${group.label}`,
    label: group.label,
    icon: group.icon,
    items: group.items.map((item) => ({
      key: item.value,
      label: item.label,
      icon: item.icon,
      active: item.value === activeUserTab.value,
      tab: item.value
    }))
  }))
})

const defaultExpandedSections = computed(() => sidebarSections.value.map((section) => section.value))
const defaultExpandedSectionsKey = computed(() => defaultExpandedSections.value.join('|'))

watch(
  defaultExpandedSectionsKey,
  async () => {
    await nextTick()

    expandedSections.value = [...defaultExpandedSections.value]

    if (sidebarCollapseRef.value) {
      sidebarCollapseRef.value.value = [...expandedSections.value]
    }
  },
  { immediate: true }
)

function syncExpandedSections() {
  const currentValue = sidebarCollapseRef.value?.value

  if (Array.isArray(currentValue)) {
    expandedSections.value = [...currentValue]
    return
  }

  expandedSections.value = typeof currentValue === 'string' && currentValue ? [currentValue] : []
}

function isSectionExpanded(sectionValue: string): boolean {
  return expandedSections.value.includes(sectionValue)
}

function handleSidebarItemClick(item: SidebarSectionItem) {
  if (item.disabled || !item.tab) return

  const next = normalizeUserTab(item.tab, canAccessUsers.value)

  void router.replace({
    query: {
      ...route.query,
      tab: next
    }
  })

  if (typeof window !== 'undefined' && window.matchMedia('(max-width: 959px)').matches) {
    closeAppSidebar()
  }
}
</script>

<style scoped>
.sidebar-shell {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding: 22px;
  box-sizing: border-box;
}

.app-sidebar::part(panel) {
  width: min(296px, 84vw);
  border-right: 1px solid rgb(var(--mdui-color-outline-variant) / 0.68);
  background: rgb(var(--mdui-color-surface-container-low));
}

.app-sidebar::part(overlay) {
  backdrop-filter: blur(8px);
}

.sidebar-nav {
  display: block;
}

.sidebar-collapse {
  display: grid;
  gap: 12px;
}

.sidebar-section {
  display: block;
}

.sidebar-section::part(body) {
  display: block;
  padding-top: 8px;
}

.sidebar-group-header::part(container),
.sidebar-list-item::part(container) {
  transition: transform 150ms ease, background-color 150ms ease, border-color 150ms ease;
}

.sidebar-group-header::part(container) {
  background: transparent;
}

.sidebar-group-label {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.sidebar-group-chevron {
  color: rgb(var(--mdui-color-on-surface-variant));
  transition: transform 180ms ease, color 180ms ease;
}

.sidebar-group-chevron--expanded {
  transform: rotate(180deg);
}

.sidebar-group-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 14px;
}

.sidebar-list-item[active]::part(container) {
  transform: translateX(4px);
}

.sidebar-list-item[disabled]::part(headline) {
  opacity: 0.9;
}

.sidebar-list-item[disabled]::part(description) {
  color: rgb(var(--mdui-color-on-surface-variant));
}

@media (max-width: 640px) {
  .sidebar-shell {
    padding: 16px;
  }
}

@media (min-width: 960px) {
  .app-sidebar {
    width: min(296px, 84vw);
  }

  .app-sidebar::part(panel) {
    width: 100%;
  }
}
</style>

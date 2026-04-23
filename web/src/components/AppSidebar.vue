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
        <mdui-collapse ref="sidebarCollapseRef" class="sidebar-collapse" :key="defaultExpandedSectionsKey" :value="expandedSections" @change="syncExpandedSections">
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
                :data-testid="item.testid ?? (section.value.startsWith('docs-') ? `api-docs-sidebar-item-${item.key}` : undefined)"
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
import { computed, ref, watch } from 'vue'
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
import { API_DOCS_SECTIONS, DOCS_OVERVIEW_PATH, getDocsSectionPath, isDocsPath } from '../content/api-docs'

type SidebarSectionItem = {
  key: string
  label: string
  icon: string
  description?: string
  disabled?: boolean
  active?: boolean
  path?: string
  tab?: UserTabValue
  testid?: string
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
        description: 'Material Bin API 使用文档',
        path: DOCS_OVERVIEW_PATH,
        testid: 'api-docs-sidebar-entry'
      }
    ]
  }
  // Temporarily hide placeholder entries in the homepage sidebar.
  // {
  //   value: 'about',
  //   label: '关于',
  //   icon: 'info',
  //   items: [
  //     {
  //       key: 'privacy-policy',
  //       label: '隐私政策',
  //       icon: 'policy',
  //       description: '占位入口，暂不实现跳转',
  //       disabled: true
  //     },
  //     {
  //       key: 'about-material-bin',
  //       label: '关于Material Bin',
  //       icon: 'info',
  //       description: '占位入口，暂不实现跳转',
  //       disabled: true
  //     }
  //   ]
  // }
]

const route = useRoute()
const router = useRouter()
const { currentUser } = useAuth()
const { isAppSidebarOpen, openAppSidebar, closeAppSidebar } = useAppSidebarState()
const sidebarCollapseRef = ref<Collapse | null>(null)

const isUsersRoute = computed(() => route.path === '/users')
const isDocsRoute = computed(() => isDocsPath(route.path))
const canAccessUsers = computed(() => currentUser.value?.role === 'admin')
const userNavigationGroups = computed(() => getUserNavigationGroups(canAccessUsers.value))
const activeUserTab = computed(() => normalizeUserTab(route.query.tab, canAccessUsers.value))
const expandedSections = ref<string[]>([])

const docsSectionsByGroup = computed(() => {
  const map = new Map<string, typeof API_DOCS_SECTIONS>()
  for (const section of API_DOCS_SECTIONS) {
    const group = map.get(section.group) || []
    group.push(section)
    map.set(section.group, group)
  }
  return map
})

const sidebarSections = computed<SidebarSection[]>(() => {
  if (isDocsRoute.value) {
    const result: SidebarSection[] = []
    for (const [groupLabel, items] of docsSectionsByGroup.value) {
      result.push({
        value: `docs-${groupLabel}`,
        label: groupLabel,
        icon: 'description',
        items: items.map((item) => ({
          key: item.slug,
          label: item.sidebarLabel,
          icon: 'article',
          path: getDocsSectionPath(item.slug),
          active: item.slug === route.params.section
        }))
      })
    }
    return result
  }

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
  () => {
    expandedSections.value = [...defaultExpandedSections.value]
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
  if (item.disabled) return

  if (item.path) {
    if (item.path !== route.path) {
      void router.push(item.path)
    }
    if (typeof window !== 'undefined' && window.matchMedia('(max-width: 959px)').matches) {
      closeAppSidebar()
    }
    return
  }

  if (item.tab) {
    const next = normalizeUserTab(item.tab, canAccessUsers.value)

    void router.replace({
      query: {
        ...route.query,
        tab: next
      }
    })
  }

  if (typeof window !== 'undefined' && window.matchMedia('(max-width: 959px)').matches) {
    closeAppSidebar()
  }
}
</script>

<style scoped>
.sidebar-shell {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding: 22px;
  box-sizing: border-box;
}

.app-sidebar {
  min-height: 0;
}

.app-sidebar::part(panel) {
  width: min(296px, 84vw);
  height: 100%;
  max-height: 100dvh;
  overflow: hidden;
  box-sizing: border-box;
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
    position: fixed !important;
    top: var(--app-header-offset, 64px) !important;
    inset-inline-start: 0 !important;
    bottom: auto !important;
    align-self: flex-start;
    width: min(296px, 84vw);
    min-height: calc(100dvh - var(--app-header-offset, 64px));
    height: calc(100dvh - var(--app-header-offset, 64px));
    overflow: hidden;
    transition:
      transform 200ms cubic-bezier(0.2, 0, 0, 1),
      top 200ms cubic-bezier(0.2, 0, 0, 1),
      height 200ms cubic-bezier(0.2, 0, 0, 1);
  }

  .app-sidebar:not([open]) {
    transform: translateX(calc(-100% - 1px));
  }

  .app-sidebar::part(panel) {
    position: absolute;
    top: 0;
    inset-inline-start: 0;
    width: 100%;
    height: 100%;
    max-height: none;
  }
}
</style>

<template>
  <div v-if="section" data-testid="api-docs-page" class="api-docs-page">
    <div data-testid="api-docs-content" class="api-docs-content">
      <p v-if="loading && !markdownContent">加载中...</p>
      <Markdown v-else :content="markdownContent" />
    </div>
  </div>

  <div v-else data-testid="api-docs-empty-state" class="api-docs-empty">
    <p>加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DOCS_OVERVIEW_PATH,
  getDocsSectionPath,
  getSectionBySlug,
  getValidSlugs
} from '@/content/api-docs'
import Markdown from '@/components/viewers/Markdown.vue'
import { getApiDocsMarkdown } from '@/services/docs'

const route = useRoute()
const router = useRouter()

const markdownContent = ref('')
const loading = ref(false)
let latestRequestId = 0
const validSlugs = new Set(getValidSlugs())

const currentSlug = computed(() => {
  const sectionParam = route.params.section
  return typeof sectionParam === 'string' ? sectionParam : undefined
})

const section = computed(() => {
  if (!currentSlug.value) return null
  return getSectionBySlug(currentSlug.value) || null
})

async function loadMarkdown(slug: string) {
  if (!validSlugs.has(slug)) {
    await router.replace(DOCS_OVERVIEW_PATH)
    return
  }

  const requestId = ++latestRequestId
  loading.value = true
  markdownContent.value = ''

  try {
    const content = await getApiDocsMarkdown(slug)
    if (requestId !== latestRequestId) return
    markdownContent.value = content
  } catch (e) {
    if (requestId !== latestRequestId) return
    console.error('Failed to load markdown content for', slug, e)
    markdownContent.value = '# 加载失败\n\n文档内容加载失败，请刷新重试。'
  } finally {
    if (requestId === latestRequestId) {
      loading.value = false
    }
  }
}

watch(
  currentSlug,
  (newSlug) => {
    if (!newSlug) {
      void router.replace(DOCS_OVERVIEW_PATH)
      return
    }

    if (!validSlugs.has(newSlug)) {
      void router.replace(DOCS_OVERVIEW_PATH)
      return
    }

    if (route.path !== getDocsSectionPath(newSlug)) {
      void router.replace(getDocsSectionPath(newSlug))
      return
    }

    void loadMarkdown(newSlug)
  },
  { immediate: true }
)
</script>

<style scoped>
.api-docs-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 0 64px;
}

.api-docs-content {
  min-height: 200px;
}

.api-docs-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

/* Responsive: ensure code blocks stay contained; tables handle their own scrolling in Markdown.vue */
.api-docs-content :deep(pre) {
  overflow-x: auto;
  max-width: 100%;
}

@media (max-width: 640px) {
  .api-docs-page {
    padding: 16px 0 48px;
  }
}
</style>

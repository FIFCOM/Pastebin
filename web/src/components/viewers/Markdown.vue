<template>
  <div ref="viewerRef" class="markdown-viewer mdui-prose" v-html="renderedHtml"></div>
  <!-- 动态主题样式 -->
  <component :is="'style'" v-text="highlightStyle"></component>

  <ImagePreview
    v-model:open="imagePreviewOpen"
    :src="imagePreviewSrc"
    :alt="imagePreviewAlt"
    :loading="imagePreviewLoading"
    :error="imagePreviewError"
    @close="closeImagePreview"
  />
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import markdownItAnchor from 'markdown-it-anchor'
import markdownItTocDoneRight from 'markdown-it-toc-done-right'
import markdownItKatex from '@vscode/markdown-it-katex'
import ImagePreview from '@/components/common/ImagePreview.vue'
import { useMbInternalImages } from '@/composables/useMbInternalImages'
import { useTheme } from '@/composables/useTheme'
import { buildMbDownloadPageHref, parseMbInternalFilePath } from '@/utils/mbFile'
// 导入主题样式
import lightTheme from 'highlight.js/styles/github.css?inline'
import darkTheme from 'highlight.js/styles/github-dark.css?inline'
import 'katex/dist/katex.min.css'

const props = defineProps<{
  content: string
  encryptionKey?: Uint8Array | null
  accessKey?: string | null
}>()

const { actualTheme } = useTheme()
const viewerRef = ref<HTMLElement | null>(null)

// 主题样式映射
const themeStyles = {
  light: lightTheme,
  dark: darkTheme
} as const

// 动态计算当前主题样式
const highlightStyle = computed(() => themeStyles[actualTheme.value])

// Used as a placeholder to avoid the broken-image icon before we hydrate/decrypt internal images.
const TRANSPARENT_1PX =
  'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='

// 初始化 markdown-it 实例
const md = new MarkdownIt({
  html: false,         // 不允许 HTML 标签
  linkify: true,       // 自动识别链接
  typographer: false,
  breaks: true,        // 将段内换行转换为 <br>
  highlight(str, lang) {
    // 官方文档推荐写法：优先使用指定语言，否则可选用自动检测或回退为转义文本
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
      } catch (__) {
        // ignore
      }
    }

    try {
      const result = hljs.highlightAuto(str)
      return result.value
    } catch (__) {
      // ignore
    }

    // 返回空字符串将交给 markdown-it 执行默认转义
    return ''
  }
})

// 启用 markdown-it-anchor：为标题生成 id
md.use(markdownItAnchor, {
  slugify: (s: string) =>
    encodeURIComponent(
      s
        .trim()
        .toLowerCase()
        .replace(/[\s]+/g, '-')
        .replace(/[()./?#]/g, '')
    ),
  tabIndex: false
})

// 启用 markdown-it-toc-done-right：支持 [toc] 或 ${toc} 生成目录
md.use(markdownItTocDoneRight, {
  containerClass: 'markdown-toc',
  listType: 'ul',
  level: [1, 2, 3, 4]
})

 // 启用 markdown-it-katex（VS Code 同款实现）：渲染行内/块级 LaTeX 公式
md.use(markdownItKatex, {
  throwOnError: false,
  errorColor: '#cc0000'
})

// ---- MaterialBin internal file links handling (encrypted blobs) ----
const defaultImageRenderer =
  md.renderer.rules.image ||
  ((tokens, idx, options, env, self) => {
    void env
    return self.renderToken(tokens, idx, options)
  })

md.renderer.rules.image = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  if (token) {
    // Enable browser-native lazy loading for all images by default.
    token.attrSet('loading', 'lazy')
    token.attrSet('decoding', 'async')

    const src = token.attrGet('src')
    const ref = src ? parseMbInternalFilePath(src) : null
    if (ref) {
      token.attrSet('src', TRANSPARENT_1PX)
      token.attrSet('data-mb-type', 'img')
      token.attrSet('data-mb-paste-id', ref.pasteId)
      token.attrSet('data-mb-file-id', ref.fileId)
    }
  }
  return defaultImageRenderer(tokens, idx, options, env, self)
}

const defaultLinkOpenRenderer =
  md.renderer.rules.link_open ||
  ((tokens, idx, options, env, self) => {
    void env
    return self.renderToken(tokens, idx, options)
  })

md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  if (token) {
    const href = token.attrGet('href')
    const ref = href ? parseMbInternalFilePath(href) : null
    if (ref) {
      token.attrSet(
        'href',
        buildMbDownloadPageHref(ref.pasteId, ref.fileId, { encryptionKeyHash: window.location.hash })
      )
      token.attrSet('data-mb-type', 'file')
      token.attrSet('data-mb-paste-id', ref.pasteId)
      token.attrSet('data-mb-file-id', ref.fileId)
    }
  }
  return defaultLinkOpenRenderer(tokens, idx, options, env, self)
}

// 渲染 Markdown
const renderedHtml = computed(() => {
  try {
    return md.render(props.content)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return `<pre><code>${props.content}</code></pre>`
  }
})

const internalImages = useMbInternalImages({
  getEncryptionKey: () => props.encryptionKey ?? null,
  getAccessKey: () => props.accessKey ?? null
})

// ---- Image preview (click-to-zoom) ----
const imagePreviewOpen = ref(false)
const imagePreviewSrc = ref('')
const imagePreviewAlt = ref('')
const imagePreviewLoading = ref(false)
const imagePreviewError = ref('')
let imagePreviewTicket = 0

function closeImagePreview() {
  imagePreviewTicket += 1
  imagePreviewOpen.value = false
  imagePreviewSrc.value = ''
  imagePreviewAlt.value = ''
  imagePreviewLoading.value = false
  imagePreviewError.value = ''
}

async function openImagePreview(img: HTMLImageElement) {
  const ticket = (imagePreviewTicket += 1)

  imagePreviewAlt.value = img.getAttribute('alt') || img.getAttribute('title') || ''
  imagePreviewError.value = ''
  imagePreviewLoading.value = true
  imagePreviewOpen.value = true
  imagePreviewSrc.value = img.currentSrc || img.src || ''

  const gen = internalImages.getGeneration()

  // Internal encrypted images: ensure we have a decrypted blob URL before showing.
  if (img.dataset.mbType === 'img') {
    const key = props.encryptionKey ?? null
    if (!key) {
      imagePreviewLoading.value = false
      imagePreviewError.value = '缺少解密密钥，无法预览该图片'
      imagePreviewSrc.value = ''
      return
    }

    await internalImages.ensureDecryptedForPreview(img, gen)

    if (ticket !== imagePreviewTicket || !imagePreviewOpen.value) return
    if (img.dataset.mbStatus === 'done') {
      imagePreviewSrc.value = img.currentSrc || img.src || ''
      imagePreviewLoading.value = false
      return
    }
    if (img.dataset.mbStatus === 'error') {
      imagePreviewLoading.value = false
      imagePreviewError.value = '图片解密失败，可点击链接下载'
      imagePreviewSrc.value = ''
      return
    }
  }

  // External images: just display the full-size source URL (we only scale via CSS in the viewer).
  imagePreviewSrc.value = img.currentSrc || img.src || ''
  imagePreviewLoading.value = false
}

// 挂载后拦截 TOC 内部链接点击，避免修改 URL hash
onMounted(() => {
  const handleClick = (event: MouseEvent) => {
    const target = event.target instanceof HTMLElement ? event.target : null
    if (!target) return

    const img = target.closest('img') as HTMLImageElement | null
    if (img && viewerRef.value?.contains(img)) {
      // Keep Ctrl/Cmd-click behavior for linked images.
      const imgLink = img.closest('a')
      if (imgLink && (event.ctrlKey || event.metaKey)) return

      // Click-to-zoom image preview (also works for external images).
      event.preventDefault()
      void openImagePreview(img)
      return
    }

    const anchor = target.closest('a')
    
    if (!anchor) return
    
    const href = anchor.getAttribute('href')
    if (!href || !href.startsWith('#')) return
    
    // 阻止默认的 hash 跳转行为
    event.preventDefault()
    
    // 提取目标 id
    const targetId = href.slice(1)
    if (!targetId) return
    
    // 查找目标元素
    const targetElement = viewerRef.value?.querySelector(`#${CSS.escape(targetId)}`)
    if (!targetElement) return
    
    // 平滑滚动到目标位置，不修改 URL
    targetElement.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
  }
  
  viewerRef.value?.addEventListener('click', handleClick)
  
  onBeforeUnmount(() => {
    viewerRef.value?.removeEventListener('click', handleClick)
  })
})

watch(
  [renderedHtml, () => props.encryptionKey, () => props.accessKey],
  async () => {
    const gen = internalImages.bumpGeneration()

    // DOM updated (v-html)
    await nextTick()

    internalImages.revokeAllBlobUrls()
    if (!viewerRef.value) return

    await internalImages.hydrateEncryptedImages(viewerRef.value, gen)
  },
  { flush: 'post', immediate: true }
)

onBeforeUnmount(() => {
  internalImages.dispose()
  closeImagePreview()
})
</script>

<style scoped>
/* 全局 Markdown 容器基础样式，遵循 MDUI 配色与排版建议 */
.markdown-viewer {
  background-color: var(--mdui-color-surface-variant);
  border-radius: 8px;
  color: var(--mdui-color-on-surface);
  line-height: 1.7;
  font-size: 0.95rem;
  overflow-x: auto;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* 标题样式 */
.markdown-viewer :deep(h1),
.markdown-viewer :deep(h2),
.markdown-viewer :deep(h3),
.markdown-viewer :deep(h4),
.markdown-viewer :deep(h5),
.markdown-viewer :deep(h6) {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.25;
  color: var(--mdui-color-on-surface);
  /* 为锚点跳转预留顶栏空间，避免标题被遮挡 */
  scroll-margin-top: 80px;
}

.markdown-viewer :deep(h1) {
  font-size: 2em;
  border-bottom: 1px solid var(--mdui-color-outline-variant);
  padding-bottom: 0.3em;
}

.markdown-viewer :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid var(--mdui-color-outline-variant);
  padding-bottom: 0.3em;
}

.markdown-viewer :deep(h3) {
  font-size: 1.25em;
}

.markdown-viewer :deep(h4) {
  font-size: 1em;
}

.markdown-viewer :deep(h5) {
  font-size: 0.875em;
}

.markdown-viewer :deep(h6) {
  font-size: 0.85em;
  color: var(--mdui-color-on-surface-variant);
}

/* 段落样式 */
.markdown-viewer :deep(p) {
  margin-top: 0;
  margin-bottom: 1em;
  color: var(--mdui-color-on-surface);
}

/* 链接样式 */
.markdown-viewer :deep(a) {
  color: rgb(var(--mdui-color-primary));
  text-decoration: none;
  border-bottom: none;
}

.markdown-viewer :deep(a:hover) {
  text-decoration: underline;
  border-bottom: none;
}

/* 列表样式 */
.markdown-viewer :deep(ul),
.markdown-viewer :deep(ol) {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 1em;
}

.markdown-viewer :deep(li) {
  margin-bottom: 0.25em;
}

/* 行内代码样式：与 Plain.vue 一致使用 MDUI surface-container 背景，统一视觉 */
.markdown-viewer :deep(code) {
  background-color: rgb(var(--mdui-color-surface-container));
  padding: 0.15em 0.35em;
  border-radius: 4px;
  font-family:
    "Fira Code",
    Menlo,
    Monaco,
    Consolas,
    "Liberation Mono",
    "SF Mono",
    /* CJK 字体，保证中文、标点正常显示 */
    "SF Pro SC",
    "PingFang SC",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    monospace;
  font-size: 0.9em;
  color: var(--mdui-color-on-surface);
}

/* 多行代码块样式：与 Plain.vue 一致使用 MDUI surface-container 背景，统一视觉 */
.markdown-viewer :deep(pre) {
  background-color: rgb(var(--mdui-color-surface-container));
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1em 0;
  font-family:
    "Fira Code",
    Menlo,
    Monaco,
    Consolas,
    "Liberation Mono",
    "SF Mono",
    "SF Pro SC",
    "PingFang SC",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    monospace;
  font-size: 0.875em;
  line-height: 1.7;
}

.markdown-viewer :deep(pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
  font-size: 0.875em;
  font-family: inherit;
}

/* 引用样式 */
.markdown-viewer :deep(blockquote) {
  padding-left: 1em;
  margin-left: 0;
  margin-right: 0;
  color: var(--mdui-color-on-surface-variant);
}

/* 水平线样式 */
.markdown-viewer :deep(hr) {
  border: none;
  border-top: 1px solid var(--mdui-color-outline-variant);
  margin: 2em 0;
}

/* 表格样式 */
.markdown-viewer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.markdown-viewer :deep(th),
.markdown-viewer :deep(td) {
  border: 1px solid var(--mdui-color-outline-variant);
  padding: 0.5em 1em;
  text-align: left;
}

.markdown-viewer :deep(th) {
  background-color: var(--mdui-color-surface);
  font-weight: 600;
}

.markdown-viewer :deep(tr:nth-child(even)) {
  background-color: var(--mdui-color-surface);
}

/* 图片样式 */
.markdown-viewer :deep(img) {
  /* Limit preview size; click to open full-size overlay. */
  max-width: min(100%, var(--mb-md-img-preview-max-width, 720px));
  max-height: var(--mb-md-img-preview-max-height, 360px);
  height: auto;
  border-radius: 8px;
  cursor: zoom-in;
  object-fit: contain;
}

/* Only treat stand-alone images as block-level to avoid breaking inline images inside text. */
.markdown-viewer :deep(p > img:only-child) {
  display: block;
  margin: 1em auto;
}

/* 强调样式 */
.markdown-viewer :deep(strong) {
  font-weight: 600;
}

.markdown-viewer :deep(em) {
  font-style: italic;
}

/* 删除线样式 */
.markdown-viewer :deep(del) {
  text-decoration: line-through;
}
</style>

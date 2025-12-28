<template>
  <div ref="vditorRef" class="vditor-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick, toRefs } from 'vue'
import Vditor from 'vditor'
import 'vditor/dist/index.css'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'paste-files', files: File[], meta: { source: 'paste' | 'drop' }): void
}>()

const { modelValue } = toRefs(props)
const vditorRef = ref<HTMLElement | null>(null)
let vditorInstance: Vditor | null = null
let pasteInterceptor: ((e: ClipboardEvent) => void) | null = null
let dropInterceptor: ((e: DragEvent) => void) | null = null

const { actualTheme } = useTheme()
const vditorTheme = ref<'classic' | 'dark'>('classic')
const isMobile = ref(false)

const checkMobile = () => {
  const mobileQuery = window.matchMedia('(max-width: 768px)')
  isMobile.value = mobileQuery.matches
  mobileQuery.addEventListener('change', (e) => {
    isMobile.value = e.matches
  })
}

const updateTheme = () => {
  vditorTheme.value = actualTheme.value === 'dark' ? 'dark' : 'classic'
}

const destroyVditor = () => {
  unbindPasteInterceptor()
  unbindDropInterceptor()
  if (vditorInstance) {
    try {
      vditorInstance.destroy()
    } catch (e) {
      console.warn('Vditor destroy error:', e)
    }
    vditorInstance = null
  }
}

const bindPasteInterceptor = () => {
  if (!vditorRef.value) return

  if (pasteInterceptor) {
    vditorRef.value.removeEventListener('paste', pasteInterceptor, true)
    pasteInterceptor = null
  }

  pasteInterceptor = (e: ClipboardEvent) => {
    const files = e.clipboardData?.files
    if (!files || files.length === 0) return

    e.preventDefault()
    e.stopPropagation()
    emit('paste-files', Array.from(files), { source: 'paste' })
  }

  vditorRef.value.addEventListener('paste', pasteInterceptor, true)
}

const unbindPasteInterceptor = () => {
  if (!vditorRef.value || !pasteInterceptor) return
  vditorRef.value.removeEventListener('paste', pasteInterceptor, true)
  pasteInterceptor = null
}

const bindDropInterceptor = () => {
  if (!vditorRef.value) return

  if (dropInterceptor) {
    vditorRef.value.removeEventListener('drop', dropInterceptor, true)
    dropInterceptor = null
  }

  dropInterceptor = (e: DragEvent) => {
    const files = e.dataTransfer?.files
    if (!files || files.length === 0) return

    e.preventDefault()
    e.stopPropagation()
    emit('paste-files', Array.from(files), { source: 'drop' })
  }

  vditorRef.value.addEventListener('drop', dropInterceptor, true)
}

const unbindDropInterceptor = () => {
  if (!vditorRef.value || !dropInterceptor) return
  vditorRef.value.removeEventListener('drop', dropInterceptor, true)
  dropInterceptor = null
}

const initVditor = async () => {
  destroyVditor()
  await nextTick()
  
  if (vditorRef.value) {
    vditorInstance = new Vditor(vditorRef.value, {
      height: '536px',
      mode: isMobile.value ? 'ir' : 'sv',
      placeholder: '请输入Markdown...',
      theme: vditorTheme.value,
      value: modelValue.value,
      cdn: import.meta.env.DEV ? '/node_modules/vditor' : '/vditor',
      tab: '\t',
      toolbar: [
        'headings', 'bold', 'italic', 'line', 'quote', 'list', 
        'ordered-list', 'check', 'code', 'inline-code', 'link', '|',
        'edit-mode', 'preview',
      ],
      counter: { enable: false, type: 'text' },
      cache: { enable: false },
      preview: {
        delay: 500,
        theme: {
          current: vditorTheme.value === 'dark' ? 'dark' : 'light',
        },
        hljs: {
          style: vditorTheme.value === 'dark' ? 'github-dark' : 'github',
        },
        mode: 'both',
        actions: []
      },
      input: (value) => {
        emit('update:modelValue', value)
      },
      after: () => {
        if (vditorInstance) {
          emit('update:modelValue', vditorInstance.getValue())
        }
        // 禁用 Vditor 默认粘贴图片(Base64)行为，改由外部上传逻辑处理
        bindPasteInterceptor()
        // 禁用 Vditor 默认拖拽图片(Base64)行为，改由外部上传逻辑处理
        bindDropInterceptor()
      }
    })
  }
}

const updateVditorTheme = () => {
  if (vditorInstance) {
    const isDark = vditorTheme.value === 'dark'
    const previewTheme = isDark ? 'dark' : 'light'
    const previewCodeTheme = isDark ? 'github-dark' : 'github'
    vditorInstance.setTheme(vditorTheme.value, previewTheme, previewCodeTheme)
  }
}

watch(modelValue, (newValue) => {
  if (vditorInstance && newValue !== vditorInstance.getValue()) {
    vditorInstance.setValue(newValue);
  }
});

watch(vditorTheme, () => {
  if (vditorInstance) {
    updateVditorTheme()
  }
})

watch(isMobile, async () => {
  if (vditorInstance) {
    const currentValue = vditorInstance.getValue()
    destroyVditor()
    await nextTick()
    initVditor()
    if(vditorInstance){
      vditorInstance.setValue(currentValue)
    }
  }
})

onMounted(() => {
  checkMobile()
  updateTheme()
  
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'class') {
        const htmlElement = mutation.target as HTMLElement
        const isDark = htmlElement.classList.contains('mdui-theme-dark')
        const newTheme = isDark ? 'dark' : 'classic'
        if (vditorTheme.value !== newTheme) {
          vditorTheme.value = newTheme
        }
      }
    })
  })
  
  const htmlElement = document.documentElement
  observer.observe(htmlElement, {
    attributes: true,
    attributeFilter: ['class']
  })
  
  nextTick(() => {
    initVditor()
  })
  
  onBeforeUnmount(() => {
    observer.disconnect()
    unbindPasteInterceptor()
    unbindDropInterceptor()
    destroyVditor()
  })
})
</script>

<style scoped>
.vditor-container {
  border: 1px solid var(--mdui-color-outline);
  border-radius: 4px;
  overflow: hidden;
}

:deep(.vditor) {
  border: none;
}

:deep(.vditor-toolbar) {
  background-color: var(--mdui-color-surface-variant);
  border-bottom: 1px solid var(--mdui-color-outline-variant);
  pointer-events: auto !important;
}

:deep(.vditor-toolbar *) {
  pointer-events: auto !important;
}

:deep(.vditor-content) {
  background-color: var(--mdui-color-surface);
}

html.mdui-theme-dark :deep(.vditor-toolbar) {
  background-color: var(--mdui-color-surface-container-high);
}

html.mdui-theme-dark :deep(.vditor-content) {
  background-color: var(--mdui-color-surface-container-low);
}
</style>

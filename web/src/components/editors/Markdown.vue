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
}>()

const { modelValue } = toRefs(props)
const vditorRef = ref<HTMLElement | null>(null)
let vditorInstance: Vditor | null = null

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
  if (vditorInstance) {
    try {
      vditorInstance.destroy()
    } catch (e) {
      console.warn('Vditor destroy error:', e)
    }
    vditorInstance = null
  }
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
<template>
  <div ref="vditorRef" class="vditor-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick, toRefs } from 'vue'
import Vditor from 'vditor'
import 'vditor/dist/index.css'
import { useTheme } from '@/composables/useTheme'
import { parseMbInternalFilePath } from '@/utils/mbFile'
import { buildMbPlainFilePath, mbSwSetPasteContext } from '@/utils/mbSw'

const props = defineProps<{
  modelValue: string
  pasteId?: string
  encryptionKey?: Uint8Array | null
  accessKey?: string | null
  adminKey?: string | null
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
let vditorDomObserver: MutationObserver | null = null
let patchScheduled = false
const swContextOk = ref(false)
let swContextTicket = 0
let lastSwContext: { pasteId: string; key: Uint8Array | null; accessKey: string | null; adminKey: string | null } = {
  pasteId: '',
  key: null,
  accessKey: null,
  adminKey: null
}

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
  unbindVditorDomObserver()
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

const ensureSwContext = async () => {
  const pasteId = (props.pasteId ?? '').trim()
  const key = props.encryptionKey ?? null
  const accessKey = props.accessKey?.trim() ? props.accessKey.trim() : null
  const adminKey = props.adminKey?.trim() ? props.adminKey.trim() : null

  if (!pasteId || !key) {
    swContextOk.value = false
    lastSwContext = { pasteId: '', key: null, accessKey: null, adminKey: null }
    return
  }

  if (
    lastSwContext.pasteId === pasteId &&
    lastSwContext.key === key &&
    lastSwContext.accessKey === accessKey &&
    lastSwContext.adminKey === adminKey &&
    swContextOk.value
  ) {
    return
  }

  lastSwContext = { pasteId, key, accessKey, adminKey }
  const ticket = (swContextTicket += 1)

  const ok = await mbSwSetPasteContext({ pasteId, encryptionKey: key, accessKey, adminKey })
  if (ticket !== swContextTicket) return

  swContextOk.value = ok
  if (ok) schedulePatchEncryptedImages()
}

const patchEncryptedInternalImages = () => {
  if (!swContextOk.value) return

  const pasteId = (props.pasteId ?? '').trim()
  if (!pasteId) return

  const root = vditorRef.value
  if (!root) return

  const imgs = Array.from(root.querySelectorAll('img')) as HTMLImageElement[]
  for (const img of imgs) {
    const rawSrc = img.getAttribute('src') || ''
    if (!rawSrc) continue

    const ref = parseMbInternalFilePath(rawSrc)
    if (!ref) continue
    if (ref.pasteId !== pasteId) continue

    const plainSrc = buildMbPlainFilePath(ref.pasteId, ref.fileId)
    if (img.getAttribute('data-mb-plain-src') === plainSrc) continue

    img.setAttribute('data-mb-orig-src', rawSrc)
    img.setAttribute('data-mb-plain-src', plainSrc)
    img.setAttribute('src', plainSrc)
  }
}

const schedulePatchEncryptedImages = () => {
  if (patchScheduled) return
  patchScheduled = true
  window.requestAnimationFrame(() => {
    patchScheduled = false
    patchEncryptedInternalImages()
  })
}

const bindVditorDomObserver = () => {
  unbindVditorDomObserver()
  if (!vditorRef.value) return

  vditorDomObserver = new MutationObserver(() => {
    schedulePatchEncryptedImages()
  })

  vditorDomObserver.observe(vditorRef.value, {
    childList: true,
    subtree: true
  })

  schedulePatchEncryptedImages()
}

const unbindVditorDomObserver = () => {
  vditorDomObserver?.disconnect()
  vditorDomObserver = null
  patchScheduled = false
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

        // Hydrate internal encrypted images in preview/IR DOM via SW plaintext path.
        bindVditorDomObserver()
        void ensureSwContext()
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

watch(
  [() => props.pasteId, () => props.encryptionKey, () => props.accessKey, () => props.adminKey],
  () => {
    void ensureSwContext()
  }
)

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
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border-radius: 4px;
  overflow: hidden;
}

:deep(.vditor) {
  box-sizing: border-box;
  width: 100% !important;
  max-width: 100%;
  min-width: 0;
  border: none;
}

:deep(.vditor-content),
:deep(.vditor-sv),
:deep(.vditor-ir),
:deep(.vditor-ir pre),
:deep(.vditor-wysiwyg),
:deep(.vditor-wysiwyg pre),
:deep(.vditor-preview),
:deep(.vditor-preview .vditor-reset) {
  min-width: 0;
  max-width: 100%;
}

:deep(.vditor-content) {
  overflow-x: hidden;
}

:deep(.vditor-sv),
:deep(.vditor-ir),
:deep(.vditor-wysiwyg),
:deep(.vditor-preview) {
  overflow-x: auto;
}

:deep(.vditor-reset pre),
:deep(.vditor-reset table) {
  max-width: 100%;
  overflow-x: auto;
}

:deep(.vditor-toolbar) {
  pointer-events: auto !important;
}

:deep(.vditor-toolbar *) {
  pointer-events: auto !important;
}


/* constrain rendered image preview size. */
:deep(.vditor-preview img:not(.emoji)),
:deep(.vditor-ir__preview img:not(.emoji)),
:deep(.vditor-wysiwyg img:not(.emoji)) {
  max-width: min(100%, var(--mb-md-img-preview-max-width, 720px));
  max-height: var(--mb-md-img-preview-max-height, 360px);
  width: auto;
  height: auto;
  border-radius: 8px;
  cursor: zoom-in;
  object-fit: contain;
}
</style>

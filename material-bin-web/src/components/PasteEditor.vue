<template>
  <div class="paste-editor">
      <!-- 标题输入框 -->
      <br></br>
      <div class="editor-section">
        <mdui-text-field
          ref="titleInputRef"
          v-model="title"
          label="标题"
          placeholder="请输入Paste标题"
          clearable
          variant="outlined"
          class="title-input"
          @keydown="handleTitleTabKey"
        ></mdui-text-field>
      </div>

      <!-- 内容类型选择 -->
      <div class="editor-section content-type-switch">
        <span>Markdown</span>
        <mdui-switch
          :checked="contentType === 'markdown'"
          @change="handleContentTypeChange"
        ></mdui-switch>
      </div>

      <!-- Plain文本输入框 -->
      <div v-show="contentType === 'plain'" class="editor-section">
        <mdui-text-field
          ref="contentInputRef"
          v-model="plainContent"
          label="正文"
          placeholder="请输入纯文本内容"
          rows="21"
          variant="outlined"
          class="content-input"
          @keydown="handleContentTabKey"
        ></mdui-text-field>
      </div>

      <!-- Markdown编辑器 -->
      <div v-show="contentType === 'markdown'" class="editor-section">
        <div ref="vditorRef" class="vditor-container"></div>
      </div>

      <!-- 操作按钮 -->
      <div class="editor-actions">
        <mdui-button
          variant="filled"
          @click="handleSubmit"
          :disabled="!canSubmit"
        >
          <mdui-icon slot="icon" name="send"></mdui-icon>
          提交
        </mdui-button>
      </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import Vditor from 'vditor'
import 'vditor/dist/index.css'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'
import 'mdui/components/switch.js'
import 'mdui/components/icon.js'
import Cookies from 'js-cookie'
import { useTheme } from '@/composables/useTheme'

// 生成随机ID的函数
const generateRandomId = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < 8; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

// 数据定义
const title = ref(`未命名的Paste.ID-${generateRandomId()}`)
const contentType = ref<'plain' | 'markdown'>('plain') // 初始值会在 onMounted 中从 Cookie 读取
const plainContent = ref('')
const markdownContent = ref('') // 添加响应式markdown内容
const vditorRef = ref<HTMLElement | null>(null)
const titleInputRef = ref<any>(null)
const contentInputRef = ref<any>(null)
let vditorInstance: Vditor | null = null

// 从 composable 获取实际主题
const { actualTheme } = useTheme()

// 使用响应式变量存储主题
const vditorTheme = ref<'classic' | 'dark'>('classic')

// 检测是否为移动设备
const isMobile = ref(false)

// 检测设备类型
const checkMobile = () => {
  // 使用 matchMedia 检测屏幕宽度
  const mobileQuery = window.matchMedia('(max-width: 768px)')
  isMobile.value = mobileQuery.matches
  
  // 监听屏幕尺寸变化
  mobileQuery.addEventListener('change', (e) => {
    isMobile.value = e.matches
  })
}

// 获取当前主题
const updateTheme = () => {
  vditorTheme.value = actualTheme.value === 'dark' ? 'dark' : 'classic'
}

// Emit事件定义
const emit = defineEmits<{
  submit: [data: { title: string; content: string; contentType: 'plain' | 'markdown' }]
}>()

// 计算属性：是否可以提交
const canSubmit = computed(() => {
  if (!title.value.trim()) return false
  
  if (contentType.value === 'plain') {
    return plainContent.value.trim().length > 0
  } else {
    return markdownContent.value.trim().length > 0
  }
})

// 销毁Vditor实例
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

// 初始化Vditor
const initVditor = async () => {
  // 先销毁已有实例
  destroyVditor()
  
  // 等待DOM更新
  await nextTick()
  
  if (vditorRef.value) {
    // console.log('Initializing Vditor...')
    vditorInstance = new Vditor(vditorRef.value, {
      height: '540px',
      mode: isMobile.value ? 'ir' : 'sv', // 移动设备使用即时渲染模式(ir)，电脑使用分屏模式(sv)
      placeholder: '请输入Markdown...',
      theme: vditorTheme.value, // 根据MDUI主题动态设置
      value: markdownContent.value, // 使用保存的内容
      cdn: import.meta.env.DEV ? '/node_modules/vditor' : '/vditor', // 开发环境使用 node_modules，生产环境使用构建后的路径
      tab: '\t', // 启用 Tab 键输入制表符
      toolbar: [
        'headings',
        'bold',
        'italic',
        // 'strike',
        // '|',
        'line',
        'quote',
        // '|',
        'list',
        'ordered-list',
        'check',
        // '|',
        'code',
        'inline-code',
        // 'insert-before',
        // 'insert-after',
        // '|',
        // 'upload',
        'link',
        // 'table',
        // '|',
        // 'undo',
        // 'redo',
        '|',
        // 'fullscreen',
        'edit-mode',
        'preview',
        // 'outline',
        // 'help'
      ],
      counter: {
        enable: false,
        type: 'text'
      },
      cache: {
        enable: false
      },
      preview: {
        delay: 500,
        theme: {
          current: vditorTheme.value === 'dark' ? 'dark' : 'light',
        },
        hljs: {
          style: vditorTheme.value === 'dark' ? 'github-dark' : 'github',
        },
        mode: 'both', // 分屏预览中的预览模式，both表示同时显示源内容和渲染内容，editor表示只显示源内容
        actions: []
      },
      input: (value) => {
        // 监听内容变化，更新响应式变量
        markdownContent.value = value
      },
      after: () => {
        // console.log('Vditor initialized successfully')
        // 初始化后更新一次内容
        if (vditorInstance) {
          markdownContent.value = vditorInstance.getValue()
        }
      }
    })
  }
}

// 动态切换Vditor主题（无需重建实例）
const updateVditorTheme = () => {
  if (vditorInstance) {
    const isDark = vditorTheme.value === 'dark'
    const previewTheme = isDark ? 'dark' : 'light'
    const previewCodeTheme = isDark ? 'github-dark' : 'github'
    
    vditorInstance.setTheme(vditorTheme.value, previewTheme, previewCodeTheme)
    // console.log('Vditor theme updated to:', vditorTheme.value, 'with code theme:', previewCodeTheme)
  }
}

// 处理内容类型切换
const handleContentTypeChange = (e: Event) => {
  const target = e.target as any
  const isMarkdown = target.checked
  contentType.value = isMarkdown ? 'markdown' : 'plain'
  // console.log('Content type changed to:', contentType.value)
  
  // 保存到 Cookie
  Cookies.set('contentType', contentType.value, { expires: 30 })
}

// 监听内容类型变化（使用v-show后无需销毁重建）
watch(contentType, (newType, oldType) => {
  // console.log('Content type changing from', oldType, 'to', newType)

  if (oldType === 'markdown' && vditorInstance) {
    // 从markdown切换出去时保存内容并同步到plain
    const mdValue = vditorInstance.getValue()
    // console.log('Markdown content before switch:', JSON.stringify(mdValue))
    // 只去除尾部空白字符，保留开头的换行符
    markdownContent.value = mdValue.trimEnd()
    plainContent.value = markdownContent.value
    // console.log('Plain content after switch:', JSON.stringify(plainContent.value))
  }

  if (oldType === 'plain' && newType === 'markdown' && vditorInstance) {
    // 从plain切换到markdown时，同步plain内容到markdown
    markdownContent.value = plainContent.value
    vditorInstance.setValue(plainContent.value)
  }
})

// 监听主题变化，使用Vditor的setTheme API动态切换（无需重建）
watch(vditorTheme, () => {
  // console.log('Theme changing from', oldTheme, 'to', newTheme)

  // 无论当前是什么模式，都更新Vditor主题（因为使用v-show，实例一直存在）
  if (vditorInstance) {
    updateVditorTheme()
  }
})

// 监听设备类型变化，这个需要重建因为要切换编辑模式
watch(isMobile, async () => {
  // console.log('Device type changing from', oldValue ? 'mobile' : 'desktop', 'to', newValue ? 'mobile' : 'desktop')

  if (contentType.value === 'markdown' && vditorInstance) {
    // 保存当前内容
    markdownContent.value = vditorInstance.getValue()
    // 销毁当前实例
    destroyVditor()
    // 重新初始化编辑器（需要切换编辑模式）
    await nextTick()
    initVditor()
  }
})

// 处理标题输入框的 Tab 键
const handleTitleTabKey = (e: KeyboardEvent) => {
  if (e.key === 'Tab') {
    e.preventDefault()
    insertTabInMduiField(titleInputRef, title)
  }
}

// 处理内容输入框的 Tab 键
const handleContentTabKey = (e: KeyboardEvent) => {
  if (e.key === 'Tab') {
    e.preventDefault()
    insertTabInMduiField(contentInputRef, plainContent)
  }
}

// 在 mdui-text-field 中插入 Tab 字符
const insertTabInMduiField = (fieldRef: any, model: any) => {
  if (!fieldRef.value) return
  
  // 获取 mdui-text-field 内部的输入元素（可能在 Shadow DOM 中）
  const textField = fieldRef.value
  let input: HTMLInputElement | HTMLTextAreaElement | null = null
  
  // 尝试从 Shadow DOM 获取
  if (textField.shadowRoot) {
    input = textField.shadowRoot.querySelector('input') ||
            textField.shadowRoot.querySelector('textarea')
  }
  
  // 如果没有 Shadow DOM，尝试直接查找
  if (!input) {
    input = textField.querySelector('input') ||
            textField.querySelector('textarea')
  }
  
  if (input) {
    const start = input.selectionStart || 0
    const end = input.selectionEnd || 0
    const value = input.value
    
    // 在光标位置插入 Tab 字符
    const newValue = value.substring(0, start) + '\t' + value.substring(end)
    input.value = newValue
    
    // 更新响应式变量
    model.value = newValue
    
    // 设置光标位置
    const newPosition = start + 1
    input.setSelectionRange(newPosition, newPosition)
    
    // 触发 input 事件
    input.dispatchEvent(new Event('input', { bubbles: true, composed: true }))
  }
}

// 处理提交
const handleSubmit = () => {
  // console.log('Submit clicked, canSubmit:', canSubmit.value)
  
  if (!canSubmit.value) {
    // console.log('Cannot submit - validation failed')
    return
  }
  
  let content = ''
  
  if (contentType.value === 'plain') {
    content = plainContent.value.trim()
  } else {
    // 确保获取最新的markdown内容
    if (vditorInstance) {
      markdownContent.value = vditorInstance.getValue()
    }
    content = markdownContent.value.trim()
  }
  
  // console.log('Submitting:', { title: title.value, contentLength: content.length, contentType: contentType.value })
  
  if (title.value.trim() && content) {
    emit('submit', {
      title: title.value.trim(),
      content,
      contentType: contentType.value
    })
  }
}


// 生命周期钩子
onMounted(() => {
  // 从 Cookie 中读取保存的内容类型偏好
  const savedContentType = Cookies.get('contentType')
  if (savedContentType === 'markdown' || savedContentType === 'plain') {
    contentType.value = savedContentType
  } else {
    // 如果没有保存的偏好，默认使用 plain
    contentType.value = 'plain'
  }
  
  // 初始化设备检测
  checkMobile()
  
  // 初始化主题
  updateTheme()
  
  // 监听主题变化事件
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'class') {
        const htmlElement = mutation.target as HTMLElement
        const isDark = htmlElement.classList.contains('mdui-theme-dark')
        const newTheme = isDark ? 'dark' : 'classic'
        
        if (vditorTheme.value !== newTheme) {
          // console.log('Theme changed via MutationObserver:', newTheme)
          vditorTheme.value = newTheme
        }
      }
    })
  })
  
  // 观察 html 元素的 class 变化
  const htmlElement = document.documentElement
  observer.observe(htmlElement, {
    attributes: true,
    attributeFilter: ['class']
  })
  
  // 初始化Markdown编辑器（使用v-show后只需初始化一次）
  nextTick(() => {
    initVditor()
  })
  
  // 清理观察器
  onBeforeUnmount(() => {
    observer.disconnect()
    destroyVditor()
  })
})
</script>

<style scoped>
.paste-editor {
  width: 100%;
  height: 100%;
  padding: 0;
}

.editor-section {
  margin-bottom: 24px;
}

.content-type-switch {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--mdui-color-surface-variant);
  border-radius: 8px;
}

.content-type-switch > span {
  font-size: 16px;
  font-weight: 500;
  color: var(--mdui-color-on-surface);
}

.title-input {
  width: 100%;
}

.content-input {
  width: 100%;
}

.vditor-container {
  border: 1px solid var(--mdui-color-outline);
  border-radius: 4px;
  overflow: hidden;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--mdui-color-outline-variant);
}

/* Vditor主题适配 */
:deep(.vditor) {
  border: none;
}

:deep(.vditor-toolbar) {
  background-color: var(--mdui-color-surface-variant);
  border-bottom: 1px solid var(--mdui-color-outline-variant);
  pointer-events: auto !important; /* 确保工具栏可点击 */
}

:deep(.vditor-toolbar *) {
  pointer-events: auto !important; /* 确保工具栏内所有元素可点击 */
}

:deep(.vditor-content) {
  background-color: var(--mdui-color-surface);
}

/* 暗色主题适配 */
html.mdui-theme-dark :deep(.vditor-toolbar) {
  background-color: var(--mdui-color-surface-container-high);
}

html.mdui-theme-dark :deep(.vditor-content) {
  background-color: var(--mdui-color-surface-container-low);
}
</style>
<template>
  <div ref="rootRef" class="plain-editor">
    <mdui-text-field
      ref="contentInputRef"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
      label="正文"
      placeholder="请输入纯文本内容"
      rows="21"
      variant="outlined"
      class="content-input"
      @keydown="handleContentTabKey"
    ></mdui-text-field>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import 'mdui/components/text-field.js'

defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'paste-files', files: File[], meta: { source: 'drop' }): void
}>()

const contentInputRef = ref<any>(null);
const rootRef = ref<HTMLElement | null>(null)
let dropInterceptor: ((e: DragEvent) => void) | null = null
let dragOverInterceptor: ((e: DragEvent) => void) | null = null

function bindDropInterceptor() {
  if (!rootRef.value) return

  if (dropInterceptor) {
    rootRef.value.removeEventListener('drop', dropInterceptor, true)
    dropInterceptor = null
  }
  if (dragOverInterceptor) {
    rootRef.value.removeEventListener('dragover', dragOverInterceptor, true)
    dragOverInterceptor = null
  }

  dragOverInterceptor = (e: DragEvent) => {
    const hasFiles =
      (e.dataTransfer?.files && e.dataTransfer.files.length > 0) ||
      (e.dataTransfer?.types && Array.from(e.dataTransfer.types).includes('Files'))
    if (!hasFiles) return
    e.preventDefault()
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
  }

  dropInterceptor = (e: DragEvent) => {
    const files = e.dataTransfer?.files
    if (!files || files.length === 0) return

    e.preventDefault()
    e.stopPropagation()
    emit('paste-files', Array.from(files), { source: 'drop' })
  }

  rootRef.value.addEventListener('dragover', dragOverInterceptor, true)
  rootRef.value.addEventListener('drop', dropInterceptor, true)
}

function unbindDropInterceptor() {
  if (!rootRef.value) return
  if (dropInterceptor) rootRef.value.removeEventListener('drop', dropInterceptor, true)
  if (dragOverInterceptor) rootRef.value.removeEventListener('dragover', dragOverInterceptor, true)
  dropInterceptor = null
  dragOverInterceptor = null
}

onMounted(() => {
  bindDropInterceptor()
})

onBeforeUnmount(() => {
  unbindDropInterceptor()
})

// 处理内容输入框的 Tab 键
const handleContentTabKey = (e: KeyboardEvent) => {
  if (e.key === 'Tab') {
    e.preventDefault();
    insertTabInMduiField(contentInputRef, e.shiftKey);
  }
};

// 在 mdui-text-field 中插入 Tab 字符或取消缩进
const insertTabInMduiField = (fieldRef: any, isUnindent: boolean = false) => {
  if (!fieldRef.value) return;
  
  const textField = fieldRef.value;
  let input: HTMLTextAreaElement | null = null;
  
  if (textField.shadowRoot) {
    input = textField.shadowRoot.querySelector('textarea');
  }
  if (!input) {
    input = textField.querySelector('textarea');
  }
  
  if (input) {
    input.focus();
    const start = input.selectionStart || 0;
    const end = input.selectionEnd || 0;
    const value = input.value;

    const lineStart = value.lastIndexOf('\n', start - 1) + 1;
    const lineEnd = end === start ? value.indexOf('\n', end) : value.indexOf('\n', end - 1);
    const actualLineEnd = lineEnd === -1 ? value.length : lineEnd;
    
    const selectionText = value.substring(lineStart, actualLineEnd);
    const lines = selectionText.split('\n');
    
    let processedText: string;
    let newStart: number;
    let newEnd: number;
    
    if (isUnindent) {
      processedText = lines.map(line => {
        if (line.startsWith('\t')) {
          return line.substring(1);
        }
        return line;
      }).join('\n');
      
      newStart = lineStart;
      newEnd = lineStart + processedText.length;
    } else {
      processedText = lines.map(line => '\t' + line).join('\n');
      newStart = lineStart;
      newEnd = lineStart + processedText.length;
    }
    
    const newValue = value.substring(0, lineStart) + processedText + value.substring(actualLineEnd);
    
    input.value = newValue;
    
    // Emit update event
    const event = new Event('input', { bubbles: true, composed: true });
    input.dispatchEvent(event);

    if (start !== end) {
      input.setSelectionRange(newStart, newEnd);
    } else {
      const cursorOffset = start - lineStart;
      if (isUnindent) {
        const firstLine = lines[0] || '';
        const removed = firstLine.startsWith('\t') ? 1 : 0;
        const newCursorPos = lineStart + Math.max(0, cursorOffset - removed);
        input.setSelectionRange(newCursorPos, newCursorPos);
      } else {
        const newCursorPos = lineStart + cursorOffset + 1;
        input.setSelectionRange(newCursorPos, newCursorPos);
      }
    }
  }
};
</script>

<style scoped>
.content-input {
  width: 100%;
}
</style>

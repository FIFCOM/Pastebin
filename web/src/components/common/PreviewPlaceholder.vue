<template>
  <div class="preview-placeholder">
    <div>{{ message }}</div>
    <div class="hint">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    message?: string
    hint?: string
  }>(),
  {
    message: '当前浏览器暂不支持在线预览。',
    hint: '请直接下载文件查看。'
  }
)
</script>

<style scoped>
.preview-placeholder {
  padding: 12px;
  border-radius: 10px;
  background-color: rgb(var(--mdui-color-surface));
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 13px;
  line-height: 1.6;
}

.preview-placeholder .hint {
  margin-top: 6px;
}
</style>


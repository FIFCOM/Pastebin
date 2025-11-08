<template>
  <div class="plain-viewer">
    <pre><code class="mdui-prose">{{ content }}</code></pre>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  content: string
}>()
</script>

<style scoped>
.plain-viewer pre {
  /* 使用 MDUI 的 surface container 设计令牌，跟随主题的灰色/容器背景 */
  background-color: rgb(var(--mdui-color-surface-container));
  padding: 1rem;
  border-radius: 8px;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

.plain-viewer code {
  /* 优先使用 Fira Code 显示 ASCII 及代码符号，中文等 CJK 字符回退到常见中文字体，最后再到系统等宽字体 */
  font-family:
    "Fira Code",
    Menlo,
    Monaco,
    Consolas,
    "Liberation Mono",
    "SF Mono",
    /* CJK 字体保证中文正常显示 */
    "SF Pro SC",
    "PingFang SC",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    /* 最后回退 */
    monospace;
  font-size: 14px;
  line-height: 1.6;
  color: var(--mdui-color-on-surface);
}
</style>
<template>
  <mdui-card class="panel-card">
    <div class="panel-header">
      <div>
        <div class="panel-title">{{ title }}</div>
        <div v-if="subtitle" class="panel-subtitle">{{ subtitle }}</div>
      </div>

      <div v-if="$slots.actions" class="panel-actions">
        <slot name="actions"></slot>
      </div>
    </div>

    <mdui-divider></mdui-divider>

    <div class="panel-content">
      <slot></slot>
    </div>
  </mdui-card>
</template>

<script setup lang="ts">
import 'mdui/components/card.js'
import 'mdui/components/divider.js'

defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped>
.panel-card {
  padding: 20px;
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.2;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.panel-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.panel-content {
  margin-top: 12px;
}

@media (max-width: 640px) {
  .panel-header {
    align-items: stretch;
    flex-direction: column;
  }

  .panel-actions {
    justify-content: flex-start;
  }
}
</style>

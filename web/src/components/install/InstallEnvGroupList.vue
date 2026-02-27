<template>
  <div v-for="group in groups" :key="groupKeyPrefix + group.name" class="env-group">
    <h3 class="group-title">{{ group.name }}</h3>
    <div class="env-grid">
      <div v-for="item in group.items" :key="item.key" class="env-item">
        <div v-if="item.key === 'DATABASE_URL'" class="database-mode-row">
          <div class="database-mode-label">数据库类型</div>
          <mdui-segmented-button-group
            :value="databaseMode"
            selects="single"
            required
            :disabled="isSubmitting"
            @change="handleDatabaseModeChange"
          >
            <mdui-segmented-button value="sqlite">SQLite</mdui-segmented-button>
            <mdui-segmented-button value="mysql">MySQL</mdui-segmented-button>
          </mdui-segmented-button-group>
          <br>
        </div>

        <mdui-text-field
          v-model="envValues[item.key]"
          :label="item.required ? `${item.key} *` : item.key"
          variant="outlined"
          :placeholder="item.key === 'DATABASE_URL' ? databaseUrlPlaceholder : item.default_value"
          :disabled="isSubmitting"
        >
          <mdui-button-icon
            v-if="canGenerateSecret(item.key)"
            slot="end-icon"
            icon="refresh"
            type="button"
            class="random-secret-icon"
            :disabled="isSubmitting"
            @click.stop="handleGenerateSecret(item.key)"
          ></mdui-button-icon>
        </mdui-text-field>

        <div v-if="item.comment && item.key !== 'DATABASE_URL'" class="env-comment">{{ item.comment }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import 'mdui/components/button-icon.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'
import 'mdui/components/text-field.js'

import type { InstallEnvItem } from '../../services/install'

type DatabaseMode = 'sqlite' | 'mysql'

type EnvGroup = {
  name: string
  items: InstallEnvItem[]
}

defineProps<{
  groups: EnvGroup[]
  groupKeyPrefix: string
  envValues: Record<string, string>
  isSubmitting: boolean
  databaseMode: DatabaseMode
  databaseUrlPlaceholder: string
  canGenerateSecret: (key: string) => boolean
}>()

const emit = defineEmits<{
  (event: 'database-mode-change', payload: Event): void
  (event: 'generate-secret', key: string): void
}>()

function handleDatabaseModeChange(event: Event) {
  emit('database-mode-change', event)
}

function handleGenerateSecret(key: string) {
  emit('generate-secret', key)
}
</script>

<style scoped>
.env-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-title {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.env-grid {
  display: grid;
  gap: 10px;
}

.env-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.random-secret-icon {
  --mdui-comp-button-icon-state-layer-color: var(--mdui-color-primary);
}

.database-mode-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.database-mode-label {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.env-comment {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
  white-space: pre-wrap;
}
</style>

<template>
  <div class="pagination-wrapper">
    <div class="pagination-summary">共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页</div>

    <div class="pagination-controls">
      <mdui-button-icon
        class="circle-action"
        title="上一页"
        aria-label="上一页"
        :aria-disabled="loading || page <= 1 ? 'true' : 'false'"
        :disabled="loading || page <= 1"
        @click="requestPage(page - 1)"
      >
        <mdui-icon name="chevron_left"></mdui-icon>
      </mdui-button-icon>

      <mdui-button-icon
        class="circle-action"
        title="下一页"
        aria-label="下一页"
        :aria-disabled="loading || page >= totalPages ? 'true' : 'false'"
        :disabled="loading || page >= totalPages"
        @click="requestPage(page + 1)"
      >
        <mdui-icon name="chevron_right"></mdui-icon>
      </mdui-button-icon>

      <template v-if="showJump">
        <mdui-text-field
          v-model="jumpPageInput"
          class="jump-field"
          label="跳转页码"
          type="number"
          variant="outlined"
          min="1"
          step="1"
          inputmode="numeric"
          :max="totalPages"
          @keydown.enter.prevent="handleJumpPage"
        ></mdui-text-field>
        <mdui-button variant="tonal" :disabled="!canJumpPage" @click="handleJumpPage">
          跳转
        </mdui-button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/icon.js'
import 'mdui/components/text-field.js'

const props = withDefaults(
  defineProps<{
    total: number
    page: number
    totalPages: number
    loading?: boolean
    showJump?: boolean
  }>(),
  {
    loading: false,
    showJump: false
  }
)

const emit = defineEmits<{
  (e: 'change-page', page: number): void
}>()

const jumpPageInput = ref('1')

watch(
  () => props.page,
  (page) => {
    jumpPageInput.value = String(page)
  },
  { immediate: true }
)

const canJumpPage = computed(() => {
  if (props.loading) return false
  const page = parsePositiveInteger(jumpPageInput.value)
  if (page === null) return false
  if (page < 1 || page > props.totalPages) return false
  return page !== props.page
})

function parsePositiveInteger(value: string): number | null {
  const normalized = value.trim()
  if (!/^\d+$/.test(normalized)) return null

  const parsed = Number(normalized)
  if (!Number.isSafeInteger(parsed) || parsed < 1) return null
  return parsed
}

function requestPage(page: number) {
  const target = Math.min(Math.max(Math.trunc(page), 1), props.totalPages)
  if (target === props.page) return
  emit('change-page', target)
}

function handleJumpPage() {
  const raw = jumpPageInput.value.trim()
  if (!raw) {
    snackbar({ message: '请输入页码', closeable: true })
    jumpPageInput.value = String(props.page)
    return
  }

  const page = parsePositiveInteger(raw)
  if (page === null) {
    snackbar({ message: '请输入正整数页码', closeable: true })
    jumpPageInput.value = String(props.page)
    return
  }

  if (page > props.totalPages) {
    snackbar({ message: `页码范围：1 - ${props.totalPages}`, closeable: true })
    jumpPageInput.value = String(props.page)
    return
  }

  requestPage(page)
}
</script>

<style scoped>
.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.65);
  background: rgb(var(--mdui-color-surface-container-low));
}

.pagination-summary {
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.jump-field {
  width: 130px;
}

.circle-action {
  border-radius: 999px;
}

@media (max-width: 640px) {
  .pagination-wrapper {
    padding: 12px 14px;
  }

  .pagination-controls {
    width: 100%;
  }

  .jump-field {
    flex: 1 1 120px;
  }
}
</style>

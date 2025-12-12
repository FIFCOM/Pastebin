<template>
  <footer class="global-footer">
    <mdui-button-icon
      class="theme-settings-btn"
      aria-label="主题设置"
      @click="openThemeDialog"
    >
      <mdui-icon-color-lens />
    </mdui-button-icon>
    <div class="footer-spacer"></div>
    <div class="footer-left">
      <span class="footer-title">Material Bin</span>
    </div>

    <mdui-dialog
      ref="themeDialogRef"
      class="theme-dialog"
      headline="主题设置"
    >
      <div class="theme-section">
        <div class="section-title">主题模式</div>
        <div class="mode-buttons">
          <mdui-segmented-button-group
            selects="single"
            :value="themeMode"
            @change="handleModeGroupChange"
          >
            <mdui-segmented-button value="auto">
              <span>自动</span>
            </mdui-segmented-button>
            <mdui-segmented-button value="light">
              <span>浅色</span>
            </mdui-segmented-button>
            <mdui-segmented-button value="dark">
              <span>深色</span>
            </mdui-segmented-button>
          </mdui-segmented-button-group>
        </div>
      </div>

      <div class="theme-section">
        <div class="section-title">预设颜色</div>
        <div class="color-palette">
          <button
            v-for="color in presetColors"
            :key="color"
            class="color-swatch"
            :style="{ backgroundColor: color }"
            :class="{ 'color-swatch--active': color === themeColor }"
            @click="changeColor(color)"
          ></button>
        </div>
      </div>

      <div class="dialog-actions">
        <mdui-button
          variant="text"
          @click="closeThemeDialog"
        >
          关闭
        </mdui-button>
      </div>
    </mdui-dialog>
  </footer>
</template>

<script setup lang="ts">
import '@mdui/icons/color-lens.js'

import { onMounted, onUnmounted, ref } from 'vue'
import 'mdui/components/button-icon.js'
import 'mdui/components/button.js'
import 'mdui/components/dialog.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'

import { useTheme, presetColors } from '../composables/useTheme'

const themeDialogRef = ref<HTMLDialogElement | null>(null)

const {
  themeMode,
  themeColor,
  setThemeMode,
  applyColor,
  initTheme,
  cleanupTheme
} = useTheme()

const openThemeDialog = () => {
  if (themeDialogRef.value) {
    ;(themeDialogRef.value as any).open = true
  }
}

const closeThemeDialog = () => {
  if (themeDialogRef.value) {
    ;(themeDialogRef.value as any).open = false
  }
}

const changeMode = (mode: 'auto' | 'light' | 'dark') => {
  setThemeMode(mode)
}

const handleModeGroupChange = (event: Event) => {
  const target = event.target as HTMLDivElement & { value?: string }
  const value = (target as any).value as string

  if (value === 'auto' || value === 'light' || value === 'dark') {
    changeMode(value)
  }
}

const changeColor = (color: string) => {
  applyColor(color)
}

onMounted(() => {
  initTheme()
})

onUnmounted(() => {
  cleanupTheme()
})
</script>

<style scoped>
.global-footer {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  color: var(--mdui-color-on-surface-variant);
  font-size: 13px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.footer-title {
  opacity: 0.75;
}

.footer-spacer {
  flex: 1;
}

.theme-settings-btn {
  --mdui-icon-size: 22px;
  transition: transform 150ms cubic-bezier(0.2, 0, 0, 1);
}

.theme-settings-btn:hover {
  transform: scale(1.08);
}

.theme-settings-btn:active {
  transform: scale(0.96);
}

.theme-dialog {
  min-width: 320px;
}

.theme-section {
  margin-top: 8px;
}

.section-title {
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--mdui-color-on-surface-variant);
}

.mode-buttons {
  display: flex;
  gap: 8px;
}

.mode-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  --mdui-button-height: 32px;
}

.mode-button--active {
  background-color: color-mix(in srgb, var(--mdui-color-primary) 12%, transparent);
}

.color-palette {
  display: flex;
  gap: 8px;
}

.color-swatch {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 2px solid transparent;
  padding: 0;
  cursor: pointer;
}

.color-swatch--active {
  border-color: var(--mdui-color-primary);
}

.dialog-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

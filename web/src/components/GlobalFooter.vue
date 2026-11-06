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
            required
            :value="themeMode"
            @click.capture="preventSelectedModeDeselect"
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

      <div class="theme-section">
        <div class="section-title">动画效果</div>
        <div class="mode-buttons">
          <mdui-segmented-button-group
            selects="single"
            required
            :value="motionLevel"
            @click.capture="preventSelectedMotionDeselect"
            @change="handleMotionGroupChange"
          >
            <mdui-segmented-button value="full">
              <span>完整</span>
            </mdui-segmented-button>
            <mdui-segmented-button value="reduced">
              <span>精简</span>
            </mdui-segmented-button>
            <mdui-segmented-button value="off">
              <span>关闭</span>
            </mdui-segmented-button>
          </mdui-segmented-button-group>
        </div>
        <p class="motion-hint">精简只保留淡入淡出,关闭则不播放任何动画。系统开启“减少动态效果”时始终关闭。</p>
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

import { pageMotion, type MotionLevel } from '../composables/page-motion'
import { useTheme, presetColors } from '../composables/useTheme'

type ThemeMode = 'auto' | 'light' | 'dark'

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

const isThemeMode = (value: string | undefined): value is ThemeMode => {
  return value === 'auto' || value === 'light' || value === 'dark'
}

const changeMode = (mode: ThemeMode) => {
  setThemeMode(mode)
}

const preventSelectedModeDeselect = (event: MouseEvent) => {
  const selectedButton = event
    .composedPath()
    .find((target) => {
      const element = target as HTMLElement
      return element.tagName === 'MDUI-SEGMENTED-BUTTON' && element.getAttribute('value') === themeMode.value
    })

  if (!selectedButton) {
    return
  }

  event.preventDefault()
  event.stopPropagation()
}

const handleModeGroupChange = (event: Event) => {
  const group = event.currentTarget as HTMLElement & { value?: string }
  const value = group.value

  if (isThemeMode(value)) {
    changeMode(value)
    return
  }

  group.value = themeMode.value
}

const motionLevel = pageMotion.level

const isMotionLevel = (value: string | undefined): value is MotionLevel => {
  return value === 'full' || value === 'reduced' || value === 'off'
}

const preventSelectedMotionDeselect = (event: MouseEvent) => {
  const selectedButton = event
    .composedPath()
    .find((target) => {
      const element = target as HTMLElement
      return element.tagName === 'MDUI-SEGMENTED-BUTTON' && element.getAttribute('value') === motionLevel.value
    })

  if (!selectedButton) {
    return
  }

  event.preventDefault()
  event.stopPropagation()
}

const handleMotionGroupChange = (event: Event) => {
  const group = event.currentTarget as HTMLElement & { value?: string }
  const value = group.value

  if (isMotionLevel(value)) {
    pageMotion.setLevel(value)
    return
  }

  group.value = motionLevel.value
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
  color: rgb(var(--mdui-color-on-surface-variant));
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
  color: rgb(var(--mdui-color-on-surface-variant));
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
  background-color: color-mix(in srgb, rgb(var(--mdui-color-primary)) 12%, transparent);
}

.motion-hint {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: rgb(var(--mdui-color-on-surface-variant));
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
  border-color: rgb(var(--mdui-color-primary));
}

.dialog-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

<template>
  <div class="steps beer" aria-label="安装进度">
    <nav class="install-stepper-nav">
      <template v-for="(step, index) in nodes" :key="step.key">
        <div class="stepper-node">
          <div
            class="button circle small fill stepper-indicator"
            :class="{
              primary: step.state !== 'pending',
              'stepper-indicator-pending': step.state === 'pending'
            }"
            :aria-current="step.state === 'active' ? 'step' : undefined"
            :aria-label="`${step.title}：${stepStateLabel(step.state)}`"
          >
            <mdui-icon v-if="step.state === 'done'" class="step-done-icon" name="done" aria-hidden="true"></mdui-icon>
            <span v-else class="step-index">{{ index + 1 }}</span>
          </div>
          <div class="stepper-content">
            <div class="step-title">{{ step.title }}</div>
            <div class="step-subtitle">{{ stepStateLabel(step.state) }}</div>
          </div>
        </div>
        <hr
          v-if="index < nodes.length - 1"
          class="max stepper-line"
          :class="{ primary: step.state === 'done' }"
          aria-hidden="true"
        >
      </template>
    </nav>
  </div>
</template>

<script setup lang="ts">
import 'mdui/components/icon.js'

type StepState = 'done' | 'active' | 'pending'

interface InstallStepNode {
  key: string
  title: string
  state: StepState
}

defineProps<{
  nodes: InstallStepNode[]
}>()

function stepStateLabel(state: StepState): string {
  if (state === 'done') return '已完成'
  if (state === 'active') return '进行中'
  return '待完成'
}
</script>

<style scoped>
.steps {
  margin: 10px 0 18px;
}

.install-stepper-nav {
  --stepper-indicator-size: 2rem;
  align-items: flex-start;
  gap: 10px;
}

.install-stepper-nav > :not(ul, ol, header, footer) {
  margin: unset;
}

.stepper-node {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
}

.stepper-indicator {
  pointer-events: none;
  cursor: default;
  user-select: none;
  inline-size: var(--stepper-indicator-size);
  block-size: var(--stepper-indicator-size);
}

.stepper-indicator-pending {
  opacity: 0.62;
}

.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1ch;
  font-weight: 600;
}

.step-done-icon {
  --mdui-icon-size: 1rem;
}

.stepper-content {
  min-width: 0;
}

.stepper-line {
  align-self: flex-start;
  margin-top: calc((var(--stepper-indicator-size) - 0.0625rem) / 2) !important;
  opacity: 0.42;
  transition: opacity 150ms cubic-bezier(0.2, 0, 0, 1);
}

.stepper-line.primary {
  opacity: 1;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
}

.step-subtitle {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

@media (max-width: 640px) {
  .install-stepper-nav {
    gap: 8px;
  }

  .step-title {
    font-size: 13px;
  }

  .step-subtitle {
    font-size: 11px;
  }
}
</style>

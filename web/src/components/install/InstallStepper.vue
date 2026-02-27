<template>
  <div class="steps" :style="{ '--step-count': String(nodes.length) }" aria-label="安装进度">
    <div class="steps-track">
      <template v-for="(step, index) in nodes" :key="step.key">
        <div
          v-if="index === 0"
          class="step-connector step-connector-head"
          :class="{ done: step.state !== 'pending' }"
          aria-hidden="true"
        ></div>

        <div class="step-node" :class="`is-${step.state}`">
          <div class="step-circle">{{ step.state === 'done' ? '✓' : index + 1 }}</div>
        </div>

        <div
          v-if="index < nodes.length - 1"
          class="step-connector step-connector-mid"
          :class="{ done: step.state === 'done' }"
          aria-hidden="true"
        ></div>

        <div
          v-else
          class="step-connector step-connector-tail"
          :class="{ done: step.state === 'done' }"
          aria-hidden="true"
        ></div>
      </template>
    </div>

    <div class="steps-content">
      <div v-for="step in nodes" :key="`content-${step.key}`" class="step-content">
        <div class="step-title">{{ step.title }}</div>
        <div class="step-subtitle">{{ stepStateLabel(step.state) }}</div>
      </div>
    </div>
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

.steps-track {
  display: flex;
  align-items: center;
}

.step-node {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.step-circle {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  border: 1px solid rgb(var(--mdui-color-outline));
  font-size: 13px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface));
  background: rgb(var(--mdui-color-surface-container));
}

.step-node.is-done .step-circle {
  color: rgb(var(--mdui-color-on-primary));
  background: rgb(var(--mdui-color-primary));
  border-color: rgb(var(--mdui-color-primary));
}

.step-node.is-active .step-circle {
  color: rgb(var(--mdui-color-primary));
  background: rgba(var(--mdui-color-primary), 0.14);
  border-color: rgba(var(--mdui-color-primary), 0.45);
}

.step-connector {
  width: 100%;
  height: 2px;
  border-radius: 999px;
  background: rgba(var(--mdui-color-outline), 0.45);
}

.step-connector-head,
.step-connector-tail {
  flex: 0.5 1 0;
}

.step-connector-mid {
  flex: 1 1 0;
  min-width: 24px;
}

.step-connector.done {
  background: rgba(var(--mdui-color-primary), 0.75);
}

.steps-content {
  min-width: 0;
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(var(--step-count), minmax(0, 1fr));
  column-gap: 0;
  row-gap: 8px;
}

.step-content {
  min-width: 0;
  text-align: center;
  padding: 0 6px;
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
  .step-circle {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  .step-connector-mid {
    min-width: 16px;
  }

  .step-title {
    font-size: 13px;
  }

  .step-subtitle {
    font-size: 11px;
  }

  .steps-content {
    column-gap: 0;
    row-gap: 6px;
  }
}
</style>

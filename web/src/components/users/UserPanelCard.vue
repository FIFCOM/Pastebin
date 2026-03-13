<template>
  <section class="panel-shell">
    <div class="panel-header">
      <div>
        <div class="panel-title">{{ title }}</div>
      </div>

      <div v-if="$slots.actions" class="panel-actions">
        <slot name="actions"></slot>
      </div>
    </div>

    <div class="panel-content">
      <slot></slot>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<style scoped>
.panel-shell {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-title {
  font-size: clamp(1.5rem, 2vw, 1.9rem);
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.panel-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.panel-content {
  min-width: 0;
}

@media (max-width: 640px) {
  .panel-shell {
    gap: 20px;
  }

  .panel-header {
    flex-direction: column;
  }

  .panel-actions {
    justify-content: flex-start;
  }
}
</style>

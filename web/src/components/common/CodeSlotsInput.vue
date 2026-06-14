<template>
  <div
    class="code-slots-input"
    :data-size="size"
    :style="rootStyle"
    @paste="handlePaste"
  >
    <label
      v-for="(_, index) in length"
      :key="index"
      class="code-slot"
      :data-filled="slotValues[index] ? 'true' : 'false'"
    >
      <span class="sr-only">{{ labelPrefix }}第 {{ index + 1 }} 位</span>
      <input
        :ref="(el) => handleInputRef(el, index)"
        :value="slotValues[index]"
        :inputmode="inputmode"
        :autocomplete="autocomplete"
        :pattern="pattern"
        :spellcheck="spellcheck"
        maxlength="1"
        :aria-label="ariaLabel"
        :disabled="disabled"
        @focus="handleInputFocus"
        @input="handleInput(index, $event)"
        @keydown="handleKeydown(index, $event)"
        @select="handleInputSelect"
      />
    </label>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

type PasteMode = 'auto' | 'replace'
type SlotSize = 'default' | 'compact'
type InputMode = 'none' | 'text' | 'tel' | 'url' | 'email' | 'numeric' | 'decimal' | 'search'

const props = withDefaults(defineProps<{
  modelValue: string
  length?: number
  ariaLabel?: string
  labelPrefix?: string
  inputmode?: InputMode
  autocomplete?: string
  pattern?: string
  spellcheck?: boolean
  disabled?: boolean
  size?: SlotSize
  pasteMode?: PasteMode
  clearPreviousOnBackspace?: boolean
  normalizer?: (raw: string) => string
}>(), {
  length: 6,
  ariaLabel: '验证码输入框',
  labelPrefix: '验证码',
  inputmode: 'numeric',
  autocomplete: 'off',
  pattern: undefined,
  spellcheck: false,
  disabled: false,
  size: 'default',
  pasteMode: 'auto',
  clearPreviousOnBackspace: true,
  normalizer: undefined
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  enter: []
  complete: [value: string]
}>()

const inputRefs = ref<Array<HTMLInputElement | null>>([])
const slotValues = ref<string[]>(createEmptySlots())

const rootStyle = computed(() => ({
  '--code-slots-length': String(props.length)
}))

watch(
  () => [props.modelValue, props.length, props.normalizer] as const,
  () => {
    const normalized = normalize(props.modelValue)
    if (slotValues.value.length === props.length && normalized === slotsToModelValue(slotValues.value)) {
      return
    }

    slotValues.value = slotsFromValue(normalized)
    if (normalized !== props.modelValue) {
      emit('update:modelValue', normalized)
    }
  },
  { immediate: true }
)

function normalize(raw: string): string {
  const normalized = props.normalizer ? props.normalizer(raw) : raw
  return normalized.slice(0, props.length)
}

function createEmptySlots(): string[] {
  return Array.from({ length: props.length }, () => '')
}

function slotsFromValue(value: string): string[] {
  const normalized = normalize(value)
  return Array.from({ length: props.length }, (_, index) => normalized[index] || '')
}

function slotsToModelValue(slots: string[]): string {
  return normalize(slots.join(''))
}

function normalizeSlots(slots: string[]): string[] {
  return Array.from({ length: props.length }, (_, index) => {
    const normalized = normalize(slots[index] || '')
    return normalized[0] || ''
  })
}

function handleInputRef(element: Element | { $el?: Element | null } | null, index: number): void {
  if (element && '$el' in element) {
    const target = element.$el
    inputRefs.value[index] = target instanceof HTMLInputElement ? target : null
    return
  }

  inputRefs.value[index] = element instanceof HTMLInputElement ? element : null
}

function focusInput(index: number): void {
  const boundedIndex = Math.min(Math.max(index, 0), props.length - 1)
  const input = inputRefs.value[boundedIndex]
  if (!input) return
  input.focus()
  collapseInputSelection(input)
}

function focus(index: number = 0): void {
  void nextTick(() => focusInput(index))
}

function collapseInputSelection(input: HTMLInputElement): void {
  const cursorIndex = input.value.length
  input.setSelectionRange(cursorIndex, cursorIndex)
}

function handleInputFocus(event: FocusEvent): void {
  const input = event.target as HTMLInputElement | null
  if (!input) return
  void nextTick(() => collapseInputSelection(input))
}

function handleInputSelect(event: Event): void {
  const input = event.target as HTMLInputElement | null
  if (!input) return
  void nextTick(() => collapseInputSelection(input))
}

function applySlots(slots: string[], nextFocusIndex?: number): void {
  const nextSlots = normalizeSlots(slots)
  const nextModelValue = slotsToModelValue(nextSlots)

  slotValues.value = nextSlots

  if (nextModelValue !== props.modelValue) {
    emit('update:modelValue', nextModelValue)
  }
  if (nextSlots.every(Boolean) && nextModelValue.length === props.length) {
    emit('complete', nextModelValue)
  }

  if (typeof nextFocusIndex === 'number') {
    focusInput(nextFocusIndex)
  }
}

function applyValue(value: string, nextFocusIndex?: number): void {
  applySlots(slotsFromValue(value), nextFocusIndex)
}

function applyFromIndex(raw: string, index: number): void {
  const normalized = normalize(raw)
  if (!normalized) return

  const nextSlots = [...slotValues.value]
  normalized.split('').forEach((char, offset) => {
    const slotIndex = index + offset
    if (slotIndex < props.length) {
      nextSlots[slotIndex] = char
    }
  })

  const nextFocusIndex = Math.min(index + normalized.length, props.length - 1)
  applySlots(nextSlots, nextFocusIndex)
}

function handleInput(index: number, event: Event): void {
  const target = event.target as HTMLInputElement | null
  const rawValue = target?.value || ''
  const normalized = normalize(rawValue)

  if (!normalized) {
    if (rawValue) {
      if (target) target.value = slotValues.value[index] || ''
      return
    }

    const nextSlots = [...slotValues.value]
    nextSlots[index] = ''
    applySlots(nextSlots)
    return
  }

  if (normalized.length > 1) {
    applyFromIndex(normalized, index)
    return
  }

  const nextSlots = [...slotValues.value]
  nextSlots[index] = normalized
  const nextFocusIndex = index < props.length - 1 ? index + 1 : index
  applySlots(nextSlots, nextFocusIndex)
}

function handleKeydown(index: number, event: KeyboardEvent): void {
  if (event.key === 'Enter') {
    event.preventDefault()
    emit('enter')
    return
  }

  if (event.key === 'Backspace') {
    if (slotValues.value[index]) {
      const nextSlots = [...slotValues.value]
      nextSlots[index] = ''
      applySlots(nextSlots)
      event.preventDefault()
      return
    }

    if (index > 0) {
      const previousIndex = index - 1
      if (props.clearPreviousOnBackspace) {
        const nextSlots = [...slotValues.value]
        nextSlots[previousIndex] = ''
        applySlots(nextSlots, previousIndex)
      } else {
        focus(previousIndex)
      }
      event.preventDefault()
    }
    return
  }

  if (event.key === 'ArrowLeft' && index > 0) {
    event.preventDefault()
    focusInput(index - 1)
    return
  }

  if (event.key === 'ArrowRight' && index < props.length - 1) {
    event.preventDefault()
    focusInput(index + 1)
  }
}

function handlePaste(event: ClipboardEvent): void {
  const rawPasted = event.clipboardData?.getData('text') || ''
  const pasted = normalize(rawPasted)
  if (!pasted) {
    if (rawPasted) event.preventDefault()
    return
  }

  event.preventDefault()
  const activeIndex = inputRefs.value.findIndex((input) => input === document.activeElement)
  const startIndex = props.pasteMode === 'replace' || pasted.length >= props.length
    ? 0
    : Math.max(activeIndex, 0)

  if (startIndex === 0 && (props.pasteMode === 'replace' || pasted.length >= props.length)) {
    applyValue(pasted, Math.min(pasted.length, props.length) - 1)
    return
  }

  applyFromIndex(pasted, startIndex)
}

defineExpose({
  focus
})
</script>

<style scoped>
.code-slots-input {
  --code-slot-gap: 8px;
  --code-slot-width: 50px;
  --code-slot-height: 54px;
  --code-slot-radius: 15px;
  --code-slot-font-size: 1.45rem;
  --code-slot-font-weight: 600;

  display: flex;
  flex-wrap: nowrap;
  gap: var(--code-slot-gap);
  justify-content: center;
  width: 100%;
}

.code-slots-input[data-size='compact'] {
  --code-slot-gap: 7px;
  --code-slot-width: 46px;
  --code-slot-height: 52px;
  --code-slot-font-size: 1.35rem;
  --code-slot-font-weight: 650;
}

.code-slot {
  display: grid;
  place-items: center;
  width: var(--code-slot-width);
  min-width: var(--code-slot-min-width, 0);
  height: var(--code-slot-height);
  border-radius: var(--code-slot-radius);
  background: rgb(var(--mdui-color-surface-container-high));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.9);
  transition: transform 150ms ease, box-shadow 150ms ease, background-color 150ms ease;
}

.code-slot[data-filled='true'] {
  background: rgb(var(--mdui-color-primary-container) / 0.5);
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-primary) / 0.24);
}

.code-slot:focus-within {
  transform: translateY(-1px);
  background: rgb(var(--mdui-color-primary-container));
  box-shadow:
    inset 0 0 0 2px rgb(var(--mdui-color-primary)),
    0 0 0 1px rgb(var(--mdui-color-primary) / 0.16);
}

.code-slot input {
  width: 100%;
  height: 100%;
  border: 0;
  padding: 0;
  background: transparent;
  caret-color: transparent;
  color: rgb(var(--mdui-color-on-surface));
  font-size: var(--code-slot-font-size);
  font-weight: var(--code-slot-font-weight);
  text-align: center;
  text-transform: uppercase;
  outline: none;
  user-select: none;
  -webkit-user-select: none;
}

.code-slot input:disabled {
  cursor: wait;
  opacity: 0.62;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 640px) {
  .code-slots-input {
    --code-slot-gap: 5px;
    --code-slot-width: 39px;
    --code-slot-height: 43px;
    --code-slot-radius: 12px;
    --code-slot-font-size: 1.08rem;
  }

  .code-slots-input[data-size='compact'] {
    --code-slot-width: min(40px, calc((100vw - 100px) / var(--code-slots-length)));
    --code-slot-min-width: 34px;
    --code-slot-height: 44px;
    --code-slot-font-size: 1.1rem;
  }
}
</style>

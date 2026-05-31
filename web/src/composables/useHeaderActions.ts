import { computed, ref, shallowRef, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'

export type HeaderActionKind = 'icon' | 'text'
type HeaderActionValue<T> = MaybeRefOrGetter<T>

export interface HeaderAction {
  id: string
  label: HeaderActionValue<string>
  ariaLabel?: HeaderActionValue<string | undefined>
  icon?: HeaderActionValue<string | undefined>
  kind?: HeaderActionValue<HeaderActionKind | undefined>
  visible?: HeaderActionValue<boolean>
  disabled?: HeaderActionValue<boolean>
  active?: HeaderActionValue<boolean>
  onClick?: () => void | Promise<void>
  flashKey?: HeaderActionValue<string | number | undefined>
}

export interface ActiveHeaderAction {
  id: string
  label: string
  ariaLabel: string
  icon?: string
  kind: HeaderActionKind
  disabled: boolean
  active: boolean
  onClick?: () => void | Promise<void>
  flashKey: string
  flashing: boolean
}

interface HeaderActionOwner {
  ownerId: string
  actions: HeaderAction[]
}

const owners = shallowRef<HeaderActionOwner[]>([])
const flashCounters = ref<Record<string, number>>({})

function resolveValue<T>(value: HeaderActionValue<T> | undefined, fallback: T): T {
  return value === undefined ? fallback : toValue(value)
}

export const activeHeaderActions = computed<ActiveHeaderAction[]>(() => {
  const owner = owners.value[owners.value.length - 1]
  if (!owner) return []

  return owner.actions.flatMap((action): ActiveHeaderAction[] => {
    if (!resolveValue(action.visible, true)) return []

    const icon = resolveValue(action.icon, undefined)
    const kind = resolveValue(action.kind, icon ? 'icon' : 'text') ?? 'text'
    const label = resolveValue(action.label, '')
    const ariaLabel = resolveValue(action.ariaLabel, undefined) || label
    const flashCounter = flashCounters.value[action.id] ?? 0
    const customFlashKey = resolveValue(action.flashKey, undefined)

    return [{
      id: action.id,
      label,
      ariaLabel,
      icon,
      kind,
      disabled: resolveValue(action.disabled, false),
      active: resolveValue(action.active, false),
      onClick: action.onClick,
      flashKey: `${action.id}:${flashCounter}:${customFlashKey ?? ''}`,
      flashing: flashCounter > 0
    }]
  })
})

export function registerHeaderActions(ownerId: string, actions: HeaderAction[]): void {
  const nextOwners = owners.value.filter((owner) => owner.ownerId !== ownerId)
  owners.value = [...nextOwners, { ownerId, actions }]
}

export function unregisterHeaderActions(ownerId: string): void {
  owners.value = owners.value.filter((owner) => owner.ownerId !== ownerId)
}

export function triggerHeaderActionFlash(actionId: string): void {
  flashCounters.value = {
    ...flashCounters.value,
    [actionId]: (flashCounters.value[actionId] ?? 0) + 1
  }
}

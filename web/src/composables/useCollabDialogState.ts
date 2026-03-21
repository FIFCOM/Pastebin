import { ref } from 'vue'

export type WorkspaceDialogIntent = 'overview' | 'share'
const PIN_ALLOWED_CHARS = new Set('ABCDEFGHJKMNPQRSTUVWXYZ0123456789'.split(''))
const PIN_CHAR_REPLACEMENTS: Record<string, string> = {
  O: '0',
  I: '1',
  L: '1'
}

const isJoinDialogOpen = ref(false)
const isWorkspaceDialogOpen = ref(false)
const pendingInvitePin = ref('')
const workspaceDialogIntent = ref<WorkspaceDialogIntent>('overview')

function normalizePin(pin: unknown): string {
  if (typeof pin !== 'string') return ''
  return pin
    .trim()
    .toUpperCase()
    .split('')
    .map((ch) => PIN_CHAR_REPLACEMENTS[ch] ?? ch)
    .filter((ch) => PIN_ALLOWED_CHARS.has(ch))
    .join('')
    .slice(0, 6)
}

export function useCollabDialogState() {
  function openJoinDialog(pin: unknown = ''): void {
    pendingInvitePin.value = normalizePin(pin)
    isWorkspaceDialogOpen.value = false
    isJoinDialogOpen.value = true
  }

  function closeJoinDialog(options: { clearInvitePin?: boolean } = {}): void {
    isJoinDialogOpen.value = false
    if (options.clearInvitePin !== false) {
      pendingInvitePin.value = ''
    }
  }

  function openWorkspaceDialog(intent: WorkspaceDialogIntent = 'overview'): void {
    workspaceDialogIntent.value = intent
    isJoinDialogOpen.value = false
    isWorkspaceDialogOpen.value = true
  }

  function closeWorkspaceDialog(): void {
    isWorkspaceDialogOpen.value = false
    workspaceDialogIntent.value = 'overview'
  }

  function clearPendingInvitePin(): void {
    pendingInvitePin.value = ''
  }

  return {
    isJoinDialogOpen,
    isWorkspaceDialogOpen,
    pendingInvitePin,
    workspaceDialogIntent,
    openJoinDialog,
    closeJoinDialog,
    openWorkspaceDialog,
    closeWorkspaceDialog,
    clearPendingInvitePin
  }
}

import { ref } from 'vue'

const isCollabDialogOpen = ref(false)

export function useCollabDialogState() {
  function openCollabDialog(): void {
    isCollabDialogOpen.value = true
  }

  function closeCollabDialog(): void {
    isCollabDialogOpen.value = false
  }

  function toggleCollabDialog(): void {
    isCollabDialogOpen.value = !isCollabDialogOpen.value
  }

  return {
    isCollabDialogOpen,
    openCollabDialog,
    closeCollabDialog,
    toggleCollabDialog
  }
}

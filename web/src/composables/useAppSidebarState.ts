import { ref } from 'vue'

const isAppSidebarOpen = ref(false)

function setAppSidebarOpen(value: boolean): void {
  isAppSidebarOpen.value = value
}

function openAppSidebar(): void {
  setAppSidebarOpen(true)
}

function closeAppSidebar(): void {
  setAppSidebarOpen(false)
}

function toggleAppSidebar(): void {
  isAppSidebarOpen.value = !isAppSidebarOpen.value
}

export function useAppSidebarState() {
  return {
    isAppSidebarOpen,
    setAppSidebarOpen,
    openAppSidebar,
    closeAppSidebar,
    toggleAppSidebar
  }
}

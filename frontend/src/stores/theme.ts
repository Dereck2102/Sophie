import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

export const useThemeStore = defineStore('theme', () => {
  const savedTheme = (localStorage.getItem('sophie_theme') ?? 'light') as ThemeMode
  const mode = ref<ThemeMode>(savedTheme)

  function applyTheme(m: ThemeMode): void {
    const isDark =
      m === 'dark' ||
      (m === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.classList.toggle('dark', isDark)
  }

  function setMode(m: ThemeMode): void {
    mode.value = m
    localStorage.setItem('sophie_theme', m)
    applyTheme(m)
  }

  // Apply on init
  applyTheme(savedTheme)

  // Watch system preference changes
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  mq.addEventListener('change', () => {
    if (mode.value === 'system') applyTheme('system')
  })

  watch(mode, applyTheme)

  return { mode, setMode }
})

<script setup lang="ts">
import { useThemeStore } from './stores/theme'
// Initialize theme on app mount
useThemeStore()
</script>

<template>
  <RouterView />
</template>

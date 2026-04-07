<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    padding?: boolean
  }>(),
  { padding: true }
)
</script>

<template>
  <div class="app-surface overflow-hidden">
    <div v-if="title" class="px-6 py-4 border-b border-slate-100/80 dark:border-slate-800/80 bg-white/40 dark:bg-slate-900/30">
      <h3 class="text-base font-semibold text-slate-800 dark:text-slate-100">{{ title }}</h3>
    </div>
    <div :class="padding ? 'p-6' : ''">
      <slot />
    </div>
  </div>
</template>

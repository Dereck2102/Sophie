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
  <div class="bg-white rounded-xl shadow-sm border border-gray-200">
    <div v-if="title" class="px-6 py-4 border-b border-gray-100">
      <h3 class="text-base font-semibold text-gray-800">{{ title }}</h3>
    </div>
    <div :class="padding ? 'p-6' : ''">
      <slot />
    </div>
  </div>
</template>

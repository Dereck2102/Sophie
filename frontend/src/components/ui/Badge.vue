<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'b2b' | 'b2c'
  }>(),
  { variant: 'default' }
)
</script>

<template>
  <span
    :class="[
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
      variant === 'default' && 'bg-gray-100 text-gray-700',
      variant === 'success' && 'bg-cyan-100 text-cyan-800',
      variant === 'warning' && 'bg-amber-100 text-amber-800',
      variant === 'danger' && 'bg-red-100 text-red-700',
      variant === 'info' && 'bg-blue-100 text-blue-700',
      variant === 'b2b' && 'bg-indigo-100 text-indigo-700',
      variant === 'b2c' && 'bg-purple-100 text-purple-700',
    ]"
  >
    <slot />
  </span>
</template>

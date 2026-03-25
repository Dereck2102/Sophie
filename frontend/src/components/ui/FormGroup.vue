<template>
  <div class="form-group">
    <label v-if="label" :for="id" class="form-label">{{ label }}</label>
    <slot></slot>
    <p v-if="help" class="form-help">{{ help }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  label?: string
  id?: string
  help?: string
}

const props = withDefaults(defineProps<Props>(), {
  id: '',
  label: '',
  help: '',
})

const id = computed(() => props.id || Math.random().toString(36).substr(2, 9))
</script>

<style scoped>
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.form-label {
  font-weight: 500;
  color: #1f2937;
  font-size: 0.875rem;
}

.form-help {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.25rem;
}
</style>

<script setup lang="ts" generic="T extends Record<string, unknown>">
defineProps<{
  columns: { key: keyof T | string; label: string; class?: string }[]
  rows: T[]
  loading?: boolean
  emptyText?: string
}>()

const emit = defineEmits<{ rowClick: [row: T] }>()
</script>

<template>
  <div class="overflow-x-auto">
    <table class="min-w-full divide-y divide-gray-200 text-sm">
      <thead class="bg-gray-50">
        <tr>
          <th
            v-for="col in columns"
            :key="String(col.key)"
            :class="['px-4 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider text-xs', col.class]"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-100">
        <tr v-if="loading">
          <td :colspan="columns.length" class="px-4 py-8 text-center text-gray-400">
            <div class="flex justify-center">
              <svg class="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
          </td>
        </tr>
        <tr v-else-if="rows.length === 0">
          <td :colspan="columns.length" class="px-4 py-8 text-center text-gray-400">
            {{ emptyText ?? 'No hay datos disponibles' }}
          </td>
        </tr>
        <tr
          v-else
          v-for="row in rows"
          :key="String((row as Record<string, unknown>).id ?? Math.random())"
          class="hover:bg-gray-50 cursor-pointer transition-colors"
          @click="emit('rowClick', row)"
        >
          <td
            v-for="col in columns"
            :key="String(col.key)"
            :class="['px-4 py-3 text-gray-700', col.class]"
          >
            <slot :name="String(col.key)" :row="row" :value="(row as Record<string, unknown>)[String(col.key)]">
              {{ (row as Record<string, unknown>)[String(col.key)] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

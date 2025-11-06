<template>
  <Navbar />
  <div class="flex-grow px-32 pt-8 overflow-y-auto bg-surface-gray-1">
    <RoundedListView v-if="groupedDocuments" :groups="groupedDocuments" />
    <LoadingIndicator v-else class="size-5 mx-auto mt-32" />
  </div>
</template>
<script setup>
import { getDocuments } from '@/resources/'
import RoundedListView from '@/components/RoundedListView.vue'
import { LoadingIndicator } from 'frappe-ui'

const groupedDocuments = computed(() => getDocuments.data && groupByTime(getDocuments.data))

function groupByTime(entities) {
  const today = new Date()
  const grouped = {
    Today: [],
    Yesterday: [],
    'Last seven days': [],
    'Earlier this month': [],
    'Earlier this year': [],
    Earlier: [],
  }
  entities
    .filter((k) => {
      k.recentDate = new Date(k.accessed || k.modified)
      return k
    })
    .sort((a, b) => b.recentDate - a.recentDate)
    .forEach((file) => {
      const yearDiff = today.getFullYear() - file.recentDate.getFullYear()
      const monthDiff = today.getMonth() - file.recentDate.getMonth() + yearDiff * 12 // Adjust for year difference
      const dayDiff = Math.floor((today - file.recentDate) / (1000 * 60 * 60 * 24))
      if (dayDiff === 0) {
        grouped['Today'].push(file)
      } else if (dayDiff <= 1) {
        grouped['Yesterday'].push(file)
      } else if (dayDiff <= 8) {
        grouped['Last seven days'].push(file)
      } else if (monthDiff === 0) {
        grouped['Earlier this month'].push(file)
      } else if (yearDiff === 0) {
        grouped['Earlier this year'].push(file)
      } else {
        grouped['Earlier'].push(file)
      }
    })
  return grouped
}
</script>

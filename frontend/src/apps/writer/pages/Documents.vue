<template>
  <Navbar />
  <div class="flex-grow overflow-hidden">
    <div class="px-15 py-5 bg-surface-gray-1">
      <h3 class="font-semibold text-base mb-4">Templates</h3>
      <div
        v-for="template in templates.data"
        class="cursor-pointer rounded w-48 border flex flex-col divide-y bg-surface-white"
        @click="
          createDocument.submit(
            { template: template.name },
            {
              onSuccess: (d) =>
                $router.push({
                  name: 'Document',
                  params: { id: d.name },
                }),
            },
          )
        "
      >
        <div v-html="template.content" class="scale-[0.5] p-3"></div>
        <div class="p-3 text-ink-gray-7 text-base">{{ template.title }}</div>
      </div>
    </div>
    <RoundedListView
      v-if="groupedDocuments"
      :groups="groupedDocuments"
      :resource="getDocuments"
    />
    <LoadingIndicator v-else class="size-5 mx-auto mt-32" />
  </div>
</template>
<script setup>
import { getDocuments, createDocument } from '@/resources/'
import RoundedListView from '@/components/RoundedListView.vue'
import { LoadingIndicator, useList } from 'frappe-ui'

const groupedDocuments = computed(
  () => getDocuments.data && groupByTime(getDocuments.data),
)

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
      const monthDiff =
        today.getMonth() - file.recentDate.getMonth() + yearDiff * 12 // Adjust for year difference
      const dayDiff = Math.floor(
        (today - file.recentDate) / (1000 * 60 * 60 * 24),
      )
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

const templates = useList({
  doctype: 'Writer Template',
  fields: ['name', 'title', 'content'],
  limit: 100,
  immediate: true,
})
</script>

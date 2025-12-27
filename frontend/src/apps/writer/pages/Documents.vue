<template>
  <Navbar />
  <div class="flex-grow overflow-y-auto bg-surface-white">
    <!-- <div v-if="templates.data?.length" class="px-15 py-5 bg-surface-gray-1">
      <h3 class="font-semibold text-base mb-3">Templates</h3>
      <div class="flex gap-10 overflow-x-scroll p-1">
        <div
          v-for="template in templates.data"
          class="cursor-pointer rounded w-48"
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
          <div
            class="aspect-[37/50] cursor-pointer overflow-hidden rounded-md dark:bg-gray-900 bg-surface-white w-48 p-3 shadow-lg transition-shadow hover:shadow-xl"
          >
            <div
              class="prose prose-sm pointer-events-none w-[200%] origin-top-left scale-[.35] prose-p:my-1 md:w-[250%] md:scale-[.19]"
              v-html="template.content"
            ></div>
          </div>
          <div class="pt-3 pl-1 text-ink-gray-7 text-base">
            {{ template.title }}
          </div>
        </div>
      </div>
    </div> -->
    <RoundedListView
      v-if="groupedDocuments"
      :groups="groupedDocuments"
      :resource="getDocuments"
    />
    <LoadingIndicator
      v-else-if="getDocuments.loading"
      class="size-5 mx-auto mt-32"
    />
    <ErrorPage v-else error="There was an error fetching documents." />
  </div>
</template>
<script setup>
import { getDocuments } from '@/resources/'
import RoundedListView from '@/components/RoundedListView.vue'
import { LoadingIndicator, usePageMeta } from 'frappe-ui'
import ErrorPage from '@/components/ErrorPage.vue'

const groupedDocuments = computed(
  () => getDocuments.data && groupByTime(getDocuments.data),
)
getDocuments.fetch()

usePageMeta(() => ({
  title: 'Writer',
}))

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
  entities.forEach((k) => {
    const modified = new Date(k.modified)
    const accessed = new Date(k.accessed)
    k.recentDate = modified > accessed ? modified : accessed
    return k
  })
  entities
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
</script>

<template>
  <div ref="container" class="px-32 pt-8 h-screen space-y-8 pb-64">
    <template v-for="[group, files] in Object.entries(groups)" :key="group">
      <template v-if="files.length">
        <h2 class="text-sm font-medium text-gray-500 uppercase tracking-wide">
          {{ group }}
        </h2>
        <div class="divide-y divide-surface-gray-2">
          <div v-for="row in files" :key="row.name">
            <div
              @click="
                $router.push({ name: 'Document', params: { id: row.name } })
              "
              class="group flex items-center justify-between px-4 py-3 hover:bg-surface-gray-1 rounded cursor-pointer"
            >
              <div class="flex gap-2">
                <div class="flex flex-col gap-1">
                  <p class="text-sm font-medium text-ink-gray-8 truncate">
                    {{ row.title }}
                  </p>
                  <div class="text-xs text-ink-gray-5">
                    {{ row.file_size_pretty }}
                  </div>
                </div>
              </div>

              <div
                class="flex items-center gap-2 text-sm text-gray-600 flex-shrink-0"
              >
                <div
                  v-if="row.owner !== $store.state.user.id"
                  class="text-xs text-ink-gray-5 flex gap-5 items-center"
                >
                  <LucideGlobe2
                    v-if="row.share_count == -2"
                    class="size-4 text-ink-gray-6"
                  />
                  <LucideBuilding2
                    v-else-if="row.share_count == -1"
                    class="size-4 text-ink-gray-6"
                  />
                  <LucideUsers
                    v-else-if="row.share_count > 0"
                    class="size-4 text-ink-gray-6"
                  />
                  <div
                    v-if="row.owner != $store.state.user.id"
                    class="flex items-center gap-1 w-16 justify-end"
                  >
                    <Avatar
                      :image="$user(row.owner)?.user_image"
                      :label="$user(row.owner)?.full_name || 'Deleted'"
                      size="xs"
                    />
                    <span :title="row.owner">{{
                      $user(row.owner)?.full_name || 'Deleted'
                    }}</span>
                  </div>
                </div>

                <span :title="row.recentDate" class="w-28 text-end">{{
                  row.relativeModified
                }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
  <!-- <ContextMenu
      v-if="rowEvent && selectedRow"
      :key="selectedRow.name"
      :action-items="dropdownActionItems(selectedRow)"
      :event="rowEvent"
      :close="() => (rowEvent = false)"
    /> -->
</template>

<script setup lang="ts">
import { computed, ref, h } from 'vue'
import { Avatar } from 'frappe-ui'
// import ContextMenu from '@/components/ContextMenu.vue'
import LucideBookOpen from '~icons/lucide/book-open'
import LucideMoreVertical from '~icons/lucide/more-vertical'
import { openEntity } from '@/utils/'
import { formatDate } from '@/utils/format'
import { useStore } from 'vuex'
import { useInfiniteScroll } from '@vueuse/core'
import router from '@/router'

const props = defineProps({
  groups: Object,
  resource: Object,
  actionItems: Array,
})

const container = useTemplateRef<HTMLElement>('container')
useInfiniteScroll(
  container,
  () => {
    if (props.resource.hasNextPage && !props.resource.loading) {
      props.resource.next()
    }
  },
  {
    distance: 10,
    canLoadMore: () => {
      return props.resource.hasNextPage
    },
  },
)

const store = useStore()
const selectedRow = ref(null)
const rowEvent = ref(null)

const contextMenu = (event, row) => {
  rowEvent.value = event
  selectedRow.value = row
}

const dropdownActionItems = (row) => {
  if (!row) return []
  return props.actionItems
    .filter((a) => !a.isEnabled || a.isEnabled(row))
    .map((a) => ({
      ...a,
      handler: () => {
        rowEvent.value = false
        store.commit('setActiveEntity', row)
        a.action([row])
      },
    }))
}
</script>

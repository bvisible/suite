<template>
  <div class="space-y-8">
    <template v-for="[group, files] in Object.entries(groups)" :key="group">
      <div v-if="files.length" class="space-y-2">
        <!-- Group Header -->
        <h2 class="text-sm font-medium text-gray-500 uppercase tracking-wide">
          {{ group }}
        </h2>

        <div
          v-for="row in files"
          :key="row.name"
          @contextmenu.prevent="(e) => contextMenu(e, row)"
          @click="$router.push({ name: 'Document', params: { id: row.name } })"
          class="group flex items-center justify-between px-4 py-3 hover:bg-surface-gray-1/60 transition-all duration-100 cursor-pointer rounded-xl bg-surface-white hover:ring-1 ring-outline-gray-2"
        >
          <div class="flex gap-2">
            <div class="flex flex-col gap-1">
              <p class="text-sm font-medium text-ink-gray-8 truncate">
                {{ row.title }}
              </p>
              <div class="text-xs text-ink-gray-5">{{ row.file_size_pretty }}</div>
            </div>
          </div>

          <div class="flex items-center gap-2 text-sm text-gray-600 flex-shrink-0">
            <div
              v-if="row.owner !== $store.state.user.id"
              class="text-xs text-ink-gray-5 flex gap-5 items-center"
            >
              <LucideGlobe2 v-if="row.share_count == -2" class="size-4 text-ink-gray-6" />
              <LucideBuilding2 v-else-if="row.share_count == -1" class="size-4 text-ink-gray-6" />
              <LucideUsers v-else-if="row.share_count > 0" class="size-4 text-ink-gray-6" />
              <div
                v-if="row.owner != $store.state.user.id"
                class="flex items-center gap-1 w-16 justify-end"
              >
                <Avatar
                  :image="$user(row.owner)?.user_image"
                  :label="$user(row.owner)?.full_name || 'Deleted user'"
                  size="xs"
                />
                <span :title="row.owner">{{ $user(row.owner)?.full_name || 'Deleted user' }}</span>
              </div>
            </div>

            <span :title="row.recentDate" class="w-28 text-end">{{ row.relativeModified }}</span>
          </div>
        </div>
      </div>
    </template>
    <!-- <ContextMenu
      v-if="rowEvent && selectedRow"
      :key="selectedRow.name"
      :action-items="dropdownActionItems(selectedRow)"
      :event="rowEvent"
      :close="() => (rowEvent = false)"
    /> -->
  </div>
</template>

<script setup>
import { computed, ref, h } from 'vue'
import { Avatar } from 'frappe-ui'
// import ContextMenu from '@/components/ContextMenu.vue'
import LucideBookOpen from '~icons/lucide/book-open'
import LucideMoreVertical from '~icons/lucide/more-vertical'
import { openEntity } from '@/utils/'
import { formatDate } from '@/utils/format'
import { useStore } from 'vuex'
import router from '@/router'

const props = defineProps({
  groups: Object,
  actionItems: Array,
})

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

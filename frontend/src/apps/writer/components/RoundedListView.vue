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
          @click="() => openEntity(row)"
          class="group flex items-center justify-between px-4 py-3 hover:bg-surface-gray-1/60 transition-all duration-100 cursor-pointer rounded-xl bg-surface-white shadow-xs hover:scale-[1.005]"
        >
          <div class="flex flex-col gap-1.5">
            <p class="text-sm font-medium text-gray-800 truncate">
              {{ row.title }}
            </p>
            <p class="text-xs text-gray-500">
              {{ row.file_size_pretty }}
            </p>
            <p v-if="row.owner !== $store.state.user.id" class="text-xs text-gray-500">
              {{ $user(row.owner).full_name }}
            </p>
          </div>

          <div class="flex items-center gap-2 text-sm text-gray-600 flex-shrink-0">
            <Button
              variant="ghost"
              class="hidden group-hover:block text-xs"
              @click.stop="(e) => contextMenu(e, row)"
            >
              Details
            </Button>
            <span>{{ row.relativeAccessed || row.relativeModified }}</span>
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
import LucideUsers from '~icons/lucide/users'
import LucideMoreVertical from '~icons/lucide/more-vertical'
import { openEntity } from '@/utils/'
import { formatDate } from '@/utils/format'
import { useStore } from 'vuex'

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

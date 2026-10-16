<template>
  <AppSettingsHeader :title="__('Statistics')" />
  <AppSettingsBody>
  <div class="flex items-center justify-between w-full mb-2">
    <!-- //// Neoffice — with a quota only; without one, the person's use and the disk the Drive writes to (storage.py,
         drive_disk), where this said « of your 0 bytes (∞ %) » (maintenance#1598) -->
    <span v-if="spaceLimit" class="text-base-medium text-ink-gray-8"
      >You have used
      {{ formatSize(usedSpace) ? formatSize(usedSpace) + ' out' : 'none' }} of your
      {{ base2BlockSize(spaceLimit) }} ({{ formatPercent((usedSpace / spaceLimit) * 100) }})</span
    >
    <!-- //// Neoffice — see above -->
    <span v-else-if="storageBreakdown.data" class="text-base-medium text-ink-gray-8">{{ withoutQuota }}</span>
  </div>
  <div
    v-if="usedSpace > 0"
    class="w-full flex justify-start items-start bg-surface-sidebar border rounded-4 overflow-clip h-7 pl-0 mb-4"
  >
    <Tooltip v-for="[file_kind, i] in storageBreakdown.data?.total" :key="file_kind">
      <template #content>
        {{ i.kind }} <br />{{ i.h_size }} ({{ i.percentageFormat }})
      </template>
      <div
        class="h-7"
        :style="{
          backgroundColor: i.color,
          width: i.percentageFormat,
          paddingRight: `${1 + i.percentageRaw}px`,
        }"
      />
    </Tooltip>
  </div>
  <div v-if="!usedSpace" class="w-full flex flex-col items-center justify-center my-10">
    <LucideCloud class="h-7 stroke-1 text-ink-gray-5" />
    <span class="text-ink-gray-8 text-sm mt-2">No Storage Used</span>
  </div>
  <div
    v-if="storageBreakdown.data?.entities?.length"
    class="mt-1 text-ink-gray-8 text-base-medium py-2"
    :class="storageBreakdown.data?.entities?.length ? 'border-b' : ''"
  >
    Large Files:
  </div>
  <div class="flex flex-col items-start justify-start w-full rounded-4 full px-1.5 overflow-y-auto">
    <div
      v-for="(i, index) in storageBreakdown.data?.entities"
      :key="i.name"
      class="w-full h-10 flex items-center justify-start py-3 gap-x-2"
      :class="index > 0 ? 'border-t' : ''"
      @mouseenter="hoveredRow = i.name"
      @mouseleave="hoveredRow = null"
    >
      <img :src="getIconUrl(i.file_type)" />
      <span class="text-ink-gray-8 text-sm truncate">{{ i.file_name }}</span>

      <div class="text-ink-gray-8 text-sm ml-auto flex items-center gap-2 h-10">
        <Button
          v-if="hoveredRow === i.name"
          variant="ghost"
          class="self-center"
          @click="openEntity(i), $emit('close')"
        >
          <LucideArrowRight class="size-4 text-ink-gray-5" />
        </Button>
        {{ formatSize(i.file_size) }}
      </div>
    </div>
  </div>
  </AppSettingsBody>
</template>
<script setup>
import { formatSize, base2BlockSize, COLOR_MAP, formatPercent } from '@/apps/drive/utils/format'
import { Tooltip, Button } from 'frappe-ui'
import AppSettingsHeader from '@/components/settings/AppSettingsHeader.vue'
import AppSettingsBody from '@/components/settings/AppSettingsBody.vue'
import { getIconUrl, openEntity, MIME_LIST_MAP } from '@/apps/drive/utils/files'
import { createResource } from 'frappe-ui'
//// Neoffice — computed: withoutQuota
import { computed, ref } from 'vue'
import LucideCloud from '~icons/lucide/cloud'

const hoveredRow = ref(null)
const usedSpace = ref(0)
const spaceLimit = ref(0)
//// Neoffice — the disk the Drive writes to (storage.py, drive_disk), and what the statistics say without a quota
const disk = ref(null)
const withoutQuota = computed(() => {
  const used = formatSize(usedSpace.value)
  if (!disk.value?.total) return __('You have used {0}.', [used])
  return __("You have used {0}. The Drive's disk: {1} used of {2}, {3} free.", [
    used,
    formatSize(disk.value.used),
    formatSize(disk.value.total),
    formatSize(disk.value.free),
  ])
})

const storageBreakdown = createResource({
  url: 'suite.drive.api.storage.storage_breakdown',
  onSuccess(data) {
    const res = {}
    usedSpace.value = 0
    spaceLimit.value = data.limit
    //// Neoffice — see withoutQuota
    disk.value = data.disk || null
    data.total.forEach((item) => {
      const kind =
        Object.entries(MIME_LIST_MAP).find(([type, list]) =>
          list.includes(item.mime_type) ? type : false
        )?.[0] || 'Unknown'
      res[kind] = res[kind] || { file_size: 0 }
      res[kind].file_size += item.file_size
      usedSpace.value += item.file_size
    })
    Object.keys(res).forEach((kind) => {
      res[kind].color = COLOR_MAP[kind]
      res[kind].kind = kind
      //// Neoffice — without a quota, the kind's share of the person's use (each kind said « ∞ % » and the bar was empty)
      res[kind].percentageRaw = (100 * res[kind].file_size) / (spaceLimit.value || usedSpace.value)
      res[kind].percentageFormat = formatPercent(res[kind].percentageRaw)
      res[kind].h_size = formatSize(res[kind].file_size)
    })
    data.total = Object.entries(res).sort((a, b) => b[1].file_size - a[1].file_size)
  },
  auto: true,
})

defineEmits(['close'])
</script>

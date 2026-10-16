<template>
  <!-- Opens the statistics page: the sidebar block is the glance, that is the detail. -->
  <SidebarStorage
    v-if="!storageBar.loading"
    class="cursor-pointer hover:bg-surface-gray-2"
    :used-percentage
    :label
    :collapsed="!isExpanded"
    @click="emitter.emit('showSettings', 'statistics')"
  />
</template>

<script setup>
import { computed, inject } from 'vue'
import SidebarStorage from '@/components/SidebarStorage.vue'
import { formatSize, base2BlockSize } from '@/apps/drive/utils/format'
import { storageBar } from '@/apps/drive/resources/files'
//// Neoffice — a quota, or the volume the Drive writes to, or the person's use alone (utils/storageGauge.js): the bar
//// said « used out of 5 GB » wherever no quota was set, a limit no server has (maintenance#1598)
import { storageGauge } from '@/apps/drive/utils/storageGauge'

const emitter = inject('emitter')

const props = defineProps(['isExpanded'])

//// Neoffice — see storageGauge
const gauge = computed(() => storageGauge(storageBar.data))

const usedPercentage = computed(() => gauge.value.percent)

//// Neoffice — the quota or the volume after the person's use, and the use alone without either
const label = computed(() =>
  gauge.value.limit
    ? formatSize(gauge.value.used) +
      ' used out of ' +
      (gauge.value.volume ? formatSize(gauge.value.limit) : base2BlockSize(gauge.value.limit))
    : formatSize(gauge.value.used) + ' used',
)

storageBar.fetch()
</script>

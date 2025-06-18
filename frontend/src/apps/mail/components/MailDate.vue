<template>
	<Tooltip :text="tooltipText" :disabled="inList">
		<div class="text-nowrap text-xs text-gray-600" :class="{ 'mr-1': !inList }">
			{{ formattedDate }}
		</div>
	</Tooltip>
</template>
<script setup lang="ts">
import { computed, inject } from 'vue'
import { useTimeAgo } from '@vueuse/core'
import { Tooltip } from 'frappe-ui'

const { datetime, inList = false } = defineProps<{ datetime: string; inList?: boolean }>()

const dayjs = inject('$dayjs')

const formattedDate = computed(() => {
	if (!inList) return __(useTimeAgo(datetime).value)
	if (dayjs(datetime).isToday()) return dayjs(datetime).format('h:mm A')
	if (dayjs(datetime).isYesterday()) return __('Yesterday')
	return dayjs(datetime).format('DD MMM YYYY')
})

const tooltipText = computed(() =>
	__(`${dayjs(datetime).format('DD MMM YYYY')} at ${dayjs(datetime).format('h:mm A')}`),
)
</script>

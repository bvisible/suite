<template>
	<Tooltip :text="tooltipText" :disabled="inList">
		<div class="text-ink-gray-5 text-nowrap text-xs" :class="{ 'mr-1': !inList }">
			{{ formattedDate }}
		</div>
	</Tooltip>
</template>
<script setup lang="ts">
import { computed, inject } from 'vue'
import { useTimeAgo } from '@vueuse/core'
import { Tooltip } from 'frappe-ui'

const {
	datetime,
	inList = false,
	clock = false,
} = defineProps<{ datetime: string; inList?: boolean; clock?: boolean }>()

const dayjs = inject('$dayjs')

const formattedDate = computed(() => {
	// The thread's day dividers already state the date, so its rows carry only the clock —
	// the sequence and the gaps between replies, which a relative stamp hides.
	//// Neoffice — `LT` and `lll`: the reader's clock and date order, not upstream's US patterns (maintenance#1321).
	if (clock) return dayjs(datetime).format('LT')
	if (!inList) {
		const timeAgo = useTimeAgo(datetime).value
		return __(timeAgo.charAt(0).toUpperCase() + timeAgo.slice(1))
	}
	//// Neoffice — `LT`, the reader's clock (maintenance#1321).
	if (dayjs(datetime).isToday()) return dayjs(datetime).format('LT')
	if (dayjs(datetime).isYesterday()) return __('Yesterday')
	if (dayjs(datetime).year() === dayjs().year()) return dayjs(datetime).format('D MMM')
	return dayjs(datetime).format('D MMM YYYY')
})

//// Neoffice — `lll` in place of « D MMM YYYY at h:mm A », which built its msgid from the date and never translated.
const tooltipText = computed(() => dayjs(datetime).format('lll'))
</script>

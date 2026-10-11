<!-- //// Neoffice — added file (no upstream equivalent): the panel of a date of the ERP (maintenance#1428).
     A task, a reminder, a booking, a leave... shown in the calendar is read-only: nothing to edit, delete or answer,
     so none of EventDetailSidebar's controls. What it offers is what the person came for: what it is, when, how it
     stands, and the way to the document that changes it. Same width and header as the event panel, so that the
     two read as one family. //// -->
<script setup lang="ts">
import { computed, inject } from 'vue'
import { ExternalLink, X } from 'lucide-vue-next'
import { Badge, Button } from 'frappe-ui'

import { fromEventZone } from '@/apps/calendar/utils/datetime'
import { formatEventWhen, isAllDayEvent } from '@/apps/calendar/utils/eventTime'
import { erpEventRoute, swatch } from '@/apps/calendar/utils/erpDates'

const { calendarEvent } = defineProps<{ calendarEvent: any }>()
const emit = defineEmits(['close'])

const dayjs = inject('$dayjs')

const calendar = computed(() => calendarEvent.calendars?.[0])
const route = computed(() => erpEventRoute(calendarEvent))

// A date of the ERP is placed the way the grid places it: whole days keep their calendar date, an hour is read in
// the reader's zone.
const when = computed(() => {
	const allDay = isAllDayEvent(calendarEvent)
	const start = allDay ? dayjs(calendarEvent.start) : fromEventZone(calendarEvent.start, calendarEvent.time_zone)
	return formatEventWhen(start, calendarEvent.duration, { allDay })
})
</script>

<template>
	<div class="bg-surface-base flex h-full w-[352px] shrink-0 flex-col overflow-hidden border-l text-left">
		<!-- Header: the source it comes from, with its colour, and the way out. -->
		<div class="flex h-12 items-center gap-3 px-4.5">
			<div class="flex min-w-0 flex-1 items-center gap-2">
				<span
					class="size-2.5 shrink-0 rounded-full"
					:style="{ backgroundColor: swatch(calendarEvent.palette) || '#9BA3AF' }"
				/>
				<span class="text-ink-gray-6 truncate text-sm">{{ calendar?.calendar_name }}</span>
			</div>
			<Button variant="ghost" :tooltip="__('Close')" @click="emit('close')">
				<X class="icon text-ink-gray-7" />
			</Button>
		</div>

		<div class="-mt-2 flex min-h-0 flex-1 flex-col overflow-y-auto">
			<div class="flex flex-col px-4.5 pb-3">
				<div class="min-w-0 space-y-1.5">
					<h3 class="text-ink-gray-8 break-words text-md font-semibold leading-6">
						{{ calendarEvent.title }}
					</h3>
					<div class="flex flex-wrap items-center gap-2 text-sm text-ink-gray-6">
						<Badge v-if="calendarEvent.late" theme="red" :label="__('Late')" />
						<span class="break-words">{{ when }}</span>
					</div>
					<div v-if="calendarEvent.meta" class="text-ink-gray-5 break-words text-sm">
						{{ calendarEvent.meta }}
					</div>
				</div>
			</div>

			<div class="border-t" />

			<div class="flex flex-col gap-3 px-4.5 py-4">
				<a
					v-if="route"
					:href="route"
					class="bg-surface-gray-2 hover:bg-surface-gray-3 text-ink-gray-8 flex w-full items-center justify-center gap-2 rounded-4 py-1.5 text-sm"
				>
					<ExternalLink class="icon size-4 shrink-0" />
					{{ __('Open the document') }}
				</a>
				<p class="text-ink-gray-5 text-xs leading-4">
					{{ __('This date comes from the ERP: open the document to change it.') }}
				</p>
			</div>
		</div>
	</div>
</template>

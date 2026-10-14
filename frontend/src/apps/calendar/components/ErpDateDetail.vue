<!-- //// Neoffice — added file (no upstream equivalent): the card of a date of the ERP (maintenance#1428).
     A task, a reminder, a booking, a leave... shown in the calendar is read-only: nothing to edit, delete or answer,
     so none of EventDetail's controls. What it offers is what the person came for: what it is, when, how it
     stands, and the way to the document that changes it. Same width, header and rows as the event card, so that the
     two read as one family; hosted where the event card is, in the popover hung on the pill (EventPopover), since
     upstream's side panel is gone. //// -->
<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import { CalendarDays, ExternalLink, X } from 'lucide-vue-next'
import { Badge, Button, Tooltip } from 'frappe-ui'

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

// Focus on the card as a whole, as EventDetail does: reka's focus scope would otherwise light the close button's
// keyboard ring as the popover opens.
const rootRef = ref<HTMLElement | null>(null)
onMounted(() => rootRef.value?.focus({ preventScroll: true }))
</script>

<template>
	<div
		ref="rootRef"
		tabindex="-1"
		class="relative flex max-h-[min(var(--reka-popover-content-available-height),40rem)] w-[352px] flex-col overflow-hidden text-left outline-none"
	>
		<!-- Header: the colour of its source, then what it is, and the way out. -->
		<div class="flex h-12 shrink-0 items-center gap-3 px-4.5">
			<div class="flex min-w-0 items-center gap-2">
				<span
					class="size-2.5 shrink-0 rounded-full"
					:style="{ backgroundColor: swatch(calendarEvent.palette) || '#9BA3AF' }"
				/>
				<Tooltip :text="calendarEvent.title" class="min-w-0">
					<h3 class="text-ink-gray-8 truncate text-md font-semibold">
						{{ calendarEvent.title }}
					</h3>
				</Tooltip>
			</div>
			<div class="ml-auto flex shrink-0 items-center gap-1">
				<Button variant="ghost" :tooltip="__('Close')" @click="emit('close')">
					<X class="icon size-3.5 text-ink-gray-7" />
				</Button>
			</div>
		</div>

		<div class="-mt-0.5 flex shrink-0 flex-col px-4.5 pb-3">
			<div class="min-w-0 space-y-1.5">
				<div class="flex flex-wrap items-center gap-2 text-sm text-ink-gray-6">
					<Badge v-if="calendarEvent.late" theme="red" :label="__('Late')" />
					<span class="break-words">{{ when }}</span>
				</div>
				<div v-if="calendarEvent.meta" class="text-ink-gray-5 break-words text-sm">
					{{ calendarEvent.meta }}
				</div>
			</div>
		</div>

		<div class="shrink-0 border-t" />

		<div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
			<!-- Whose it is: a date of the ERP has no organizer, so the source it comes from. -->
			<div v-if="calendar?.calendar_name" class="flex items-center gap-2.5 px-4.5 py-3">
				<CalendarDays class="icon text-ink-gray-5 size-4 shrink-0" />
				<span class="text-ink-gray-7 min-w-0 truncate text-sm">{{ calendar.calendar_name }}</span>
			</div>

			<div v-if="calendar?.calendar_name" class="border-t" />

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
					{{ __('This date comes from Neoffice: open the document to change it.') }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, reactive, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, Calendar, Dialog, createResource, usePageMeta } from 'frappe-ui'

import { raiseToast } from '@/utils'
import { userStore } from '@/stores/user'
import AppSidebar from '@/components/AppSidebar.vue'
import EventPopoverContent from '@/components/EventPopoverContent.vue'
import EventModal from '@/components/Modals/EventModal.vue'

const dayjs = inject('$dayjs')

const { identities } = userStore()

const route = useRoute()
const router = useRouter()

const calendarRef = useTemplateRef('calendar')

usePageMeta(() => ({ title: calendarRef.value?.currentMonthYear || __('Frappe Calendar') }))

watch(
	() => [
		calendarRef.value?.currentYear,
		calendarRef.value?.currentMonth,
		calendarRef.value?.currentDay,
	],
	([year, month], [oldYear, oldMonth]) => {
		if (year !== oldYear || month !== oldMonth) events.reload()
		setRoute()
	},
)

watch(
	() => calendarRef.value?.activeView,
	(view) => {
		if (view && view !== route.name) setRoute()
	},
)

const setRoute = () => {
	const year = calendarRef.value?.currentYear
	const month = calendarRef.value?.currentMonth
	const day = calendarRef.value?.currentDay

	const target = dayjs().year(year).month(month).date(day)
	const view = calendarRef.value?.activeView as 'Month' | 'Week' | 'Day'

	console.log(year, month, day)
	if (dayjs().isSame(target, view)) router.replace({ name: view })
	else router.push({ name: view, params: { year, month: month + 1, day } })
}

onMounted(() => {
	if (route.name) calendarRef.value.activeView = route.name

	const { year, month, day } = route.params
	if (year && month && day) {
		const date = dayjs(`${year}-${month}-${day}`, 'YYYY-M-D')
		if (date.isValid()) calendarRef.value.setCalendarDate(date)
	}
})

const transformEvent = (event) => {
	const start = dayjs(event.start)
	const dur = dayjs.duration(event.duration || 'PT0S')
	const end = start.add(dur)
	const isAllDay =
		start.hour() === 0 &&
		start.minute() === 0 &&
		start.second() === 0 &&
		dur.days() > 0 &&
		dur.hours() === 0 &&
		dur.minutes() === 0 &&
		dur.seconds() === 0

	return {
		...event,
		fromDate: start.format('YYYY-MM-DD'),
		toDate: end.format('YYYY-MM-DD'),
		fromTime: start.format('HH:mm'),
		toTime: end.format('HH:mm'),
		role: getEventRole(event),
		isAllDay,
	}
}

const getEventRole = (event) => {
	if (identities.data.some((id) => id.email === event.organizer.replace('mailto:', '')))
		return 'Organizer'
	if (
		identities.data.some((id) =>
			event.participants?.some((p) => p.email.replace('mailto:', '') === id.email),
		)
	)
		return 'Attendee'
	return 'Viewer'
}

const calendars = createResource({
	url: 'calendar_app.api.get_calendars',
	auto: true,
	onSuccess: (data) => (visibleCalendars.value = data.map((cal) => cal.name)),
	onError: (error) => raiseToast(error.message, 'error'),
})

const visibleCalendars = ref<string[]>([])

const events = createResource({
	url: 'calendar_app.api.get_calendar_events',
	makeParams: () => {
		const date = dayjs()
			.year(calendarRef.value?.currentYear)
			.month(calendarRef.value?.currentMonth)
		return {
			from_date: date.startOf('month').subtract(37, 'day').toDate(),
			to_date: date.endOf('month').add(37, 'day').toDate(),
			time_zone: dayjs.tz.guess(),
		}
	},
	transform: (data) => data.map(transformEvent),
	onError: (error) => raiseToast(error.message, 'error'),
})

const visibleEvents = computed(
	() =>
		events.data?.filter((event) =>
			event.calendars
				.map((c) => c.calendar)
				.some((cal) => visibleCalendars.value.includes(cal)),
		) || [],
)

const showEditEvent = ref(false)

const event = reactive({})

const handleOpenEvent = (e) => {
	Object.assign(event, e)
	showEditEvent.value = true
}

watch(
	() => showEditEvent.value,
	(val) => {
		if (!val) Object.keys(event).forEach((key) => delete event[key])
	},
)

const eventToBeUpdated = reactive({})
const showRecurringEventModal = ref(false)
const isUpdateInstance = ref(false)
const showNotifyModal = ref(false)

const handleUpdate = (e) => {
	Object.assign(eventToBeUpdated, e)
	if (e.recurrence_id) showRecurringEventModal.value = true
	else handleUpdateEvent()
}

const handleUpdateRecurringEvent = (updateInstance: boolean) => {
	isUpdateInstance.value = updateInstance
	showRecurringEventModal.value = false
	handleUpdateEvent()
}

const handleUpdateEvent = () => {
	if (hasParticipantsOtherThanUser.value) showNotifyModal.value = true
	else submitEvent(false)
}

const hasParticipantsOtherThanUser = computed(
	() =>
		eventToBeUpdated.participants?.some((p) =>
			identities.data.every((i) => i.email !== p.email),
		) ?? false,
)

const submitEvent = (sendEmail: boolean) => {
	if (isUpdateInstance.value) {
		return
	}

	eventToBeUpdated.start = dayjs(eventToBeUpdated.fromDateTime).format('YYYY-MM-DDTHH:mm:ss')
	if (!eventToBeUpdated.isAllDay) {
		const start = dayjs(eventToBeUpdated.fromDateTime)
		const end = dayjs(eventToBeUpdated.toDateTime)
		const diff = dayjs.duration(end.diff(start))
		const hours = Math.floor(diff.asHours())
		const minutes = diff.minutes()
		eventToBeUpdated.duration = dayjs.duration({ hours, minutes }).toISOString()
	}
	editEvent.submit({ sendEmail })
}

// const editEventInstance = createResource({
// 	url: 'mail.client.doctype.calendar_event.calendar_event.update_calendar_event_instance',
// 	makeParams: ({ sendEmail }: { sendEmail: boolean }) => ({
// 		user: user.data.name,
// 		master_id: selectedEvent.calendarEvent.master_id,
// 		recurrence_id: selectedEvent.calendarEvent.recurrence_id,
// 		patch: patch.value,
// 		send_scheduling_messages: sendEmail,
// 	}),
// })

const editEvent = createResource({
	url: 'mail.client.doctype.calendar_event.calendar_event.update_calendar_event',
	makeParams: ({ sendEmail }: { sendEmail: boolean }) => ({
		...eventToBeUpdated,
		id: eventToBeUpdated.master_id,
		send_scheduling_messages: sendEmail,
	}),
})

const RECURRING_EVENT_MODAL_OPTIONS = {
	title: __('Update Recurring Event'),
	icon: { name: 'repeat' },
	message: __('Do you want to update just this instance, or all events in the series?'),
}

const NOTIFY_MODAL_OPTIONS = {
	title: __('Notify Participants'),
	icon: { name: 'bell' },
	message: __('Send an email to let attendees know this event has been updated?'),
}
</script>

<template>
	<div class="flex h-screen min-h-0 w-full min-w-0 flex-col">
		<div class="flex min-h-0 min-w-0 flex-1">
			<AppSidebar
				:calendars="calendars?.data || []"
				:visible-calendars
				@update:visible-calendars="
					(name) =>
						visibleCalendars.includes(name)
							? visibleCalendars.splice(visibleCalendars.indexOf(name), 1)
							: visibleCalendars.push(name)
				"
			/>
			<div class="min-h-0 min-w-0 flex-1 p-4">
				<Calendar
					ref="calendar"
					:events="visibleEvents"
					:config="{ isEditMode: true }"
					:on-dbl-click="(event) => handleOpenEvent(event)"
					:on-cell-click="(event) => handleOpenEvent(event)"
					@update="handleUpdate"
				>
					<template #event-popover-content="{ calendarEvent, close }">
						<EventPopoverContent
							:calendar-event
							:close
							@edit="handleOpenEvent({ calendarEvent })"
							@reload-events="events.reload()"
						/>
					</template>
				</Calendar>
			</div>
		</div>
	</div>
	<EventModal v-model="showEditEvent" :selected-event="event" @reload-events="events.reload()" />
	<Dialog v-model="showRecurringEventModal" :options="RECURRING_EVENT_MODAL_OPTIONS">
		<template #actions>
			<div class="flex justify-end space-x-2">
				<Button @click="handleUpdateRecurringEvent(false)">
					{{ __('Entire series') }}
				</Button>
				<!-- <Button variant="solid" @click="handleUpdateRecurringEvent(true)">
					{{ __('This instance') }}
				</Button> -->
			</div>
		</template>
	</Dialog>
	<Dialog v-model="showNotifyModal" :options="NOTIFY_MODAL_OPTIONS">
		<template #actions>
			<div class="flex justify-end space-x-2">
				<Button variant="outline" @click="submitEvent(false)"> {{ __('Skip') }} </Button>
				<Button variant="solid" @click="submitEvent(true)">
					{{ __('Send Email') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

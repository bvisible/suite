<!-- //// Neoffice: new file — Calendar flavor of the shared NeoCockpit chrome.
     Replaces the native AppSidebar with the Neoffice menu + a Calendars section:
     colour swatch (filled=visible / hollow=hidden), a shared indicator, and a
     per-calendar gear opening full settings (rename / colour / share / CalDAV /
     delete). Falls back to AppSidebar on failure. //// -->
<template>
	<AppSidebar
		v-if="failed"
		v-bind="$attrs"
		:calendars="calendars"
		:visible-calendars="visibleCalendars"
		@update:visible-calendars="(n: string) => emit('update:visibleCalendars', n)"
	/>
	<template v-else>
		<NeoCockpitBridge
			:surface-app="surfaceApp"
			:context-nav="contextNav"
			:navigate="(r: string) => router.push(r)"
			@failed="failed = true"
		/>
		<NewCalendarModal v-model="showNew" :account="account" @created="emit('reload')" />
		<!-- //// Neoffice — the agenda as a private iCal address for Google, Outlook and Apple (maintenance#1428). -->
		<CalendarFeedModal v-model="showFeed" />
		<CalendarSettingsModal
			v-if="editing"
			v-model="showSettings"
			:account="account"
			:calendar="editing"
			@reload="emit('reload')"
		/>
	</template>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import calendarLogo from '@/assets/app-logos/calendar.svg'
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import AppSidebar from '@/apps/calendar/components/AppSidebar.vue'
import NewCalendarModal from '@/apps/calendar/components/Modals/NewCalendarModal.vue'
//// Neoffice — share the agenda as a private iCal address (maintenance#1428, suite/calendar/feed.py).
import CalendarFeedModal from '@/apps/calendar/components/Modals/CalendarFeedModal.vue'
import CalendarSettingsModal from '@/apps/calendar/components/Modals/CalendarSettingsModal.vue'
import { userStore } from '@/apps/calendar/stores/user'
//// Neoffice — the dates of the ERP, a group of read-only calendars of their own (maintenance#1428).
import { isErpCalendar, swatch } from '@/apps/calendar/utils/erpDates'

//// Neoffice — `inheritAttrs: false` + `v-bind="$attrs"` on the fallback: upstream's
//// AppSidebar grew a mini-month and an event list (month/year/day/view/events/
//// selectedEvent, @select-date, @select-event) after the merge of 31.08.2026. This
//// chrome does not read them itself, but it must not swallow them either — they are
//// relayed untouched so the fallback keeps upstream's full behaviour.
defineOptions({ inheritAttrs: false })

const { calendars, visibleCalendars, erpScope, erpScoped } = defineProps<{
	calendars: any[]
	visibleCalendars: string[]
	//// Neoffice — whose dates the sources of the ERP show, and whether the person can choose (maintenance#1428).
	erpScope?: string
	erpScoped?: boolean
}>()
//// Neoffice — toggleErpScope: the person asks for the other scope (maintenance#1428).
const emit = defineEmits(['update:visibleCalendars', 'reload', 'toggleErpScope'])

const router = useRouter()
const store = userStore()
const failed = ref(false)
const showNew = ref(false)
//// Neoffice — the feed modal (maintenance#1428).
const showFeed = ref(false)
const showSettings = ref(false)
const editing = ref<any>(null)

const account = computed(() => store.accountId)
const surfaceApp = { name: 'calendar', title: 'Calendar', logo: calendarLogo }

function openSettings(c: any) {
	editing.value = c
	showSettings.value = true
}

//// Neoffice — the person's own calendars, then the dates of the ERP: read-only, switched like them, no gear and
//// nothing to change from here (maintenance#1428).
const ownCalendars = computed(() => calendars.filter((c) => !isErpCalendar(c)))
const erpItems = computed(() => [
	...calendars
		.filter((c) => isErpCalendar(c))
		.map((c) => ({
			label: c._name,
			color: swatch(c.palette) || '#9BA3AF',
			dim: !visibleCalendars.includes(c.name),
			onClick: () => emit('update:visibleCalendars', c.name),
		})),
	// Whose dates the sources show: only the ones that have an owner (tasks, leaves...) depend on it.
	...(erpScoped
		? [
			{
				label: erpScope === 'all' ? __('Everyone’s dates') : __('My dates'),
				//// Neoffice — the cockpit draws the icons of its own map: `user-check` and `users` are in it, a plain `user` is not.
				icon: erpScope === 'all' ? 'lucide-users' : 'lucide-user-check',
				onClick: () => emit('toggleErpScope'),
			},
		]
		: []),
])

const contextNav = computed(() => [
	{
		label: __('Calendars'),
		items: [
			// //// Neoffice: colour swatch (filled=visible, hollow=hidden), a
			// "shared" icon+tooltip, and a gear opening the calendar settings.
			// Click on the row toggles visibility. ////
			...ownCalendars.value.map((c) => {
				const sharedCount = (c.share_with || []).length
				return {
					label: c._name,
					//// Neoffice — swatch(): a palette name drawn with the ink variable the grid uses (maintenance#1428).
					color: swatch(c.color) || '#9BA3AF',
					dim: !visibleCalendars.includes(c.name),
					shared: sharedCount > 0,
					sharedTitle: !sharedCount
						? undefined
						: sharedCount === 1
							? __('Shared with 1 person')
							: __('Shared with {0} people', [sharedCount]),
					onGear: () => openSettings(c),
					onClick: () => emit('update:visibleCalendars', c.name),
				}
			}),
			{ label: __('Add a calendar'), icon: 'lucide-plus', onClick: () => (showNew.value = true) },
			//// Neoffice — the agenda, read by Google, Outlook and Apple through a private address (maintenance#1428).
			{ label: __('Share your agenda'), icon: 'lucide-share-2', onClick: () => (showFeed.value = true) },
		],
	},
	//// Neoffice — then the dates of the ERP, when the site has any for this person (maintenance#1428).
	...(erpItems.value.length ? [{ label: __('Dates of the ERP'), items: erpItems.value }] : []),
])
</script>

<!-- //// Neoffice: new file — Calendar flavor of the shared NeoCockpit chrome.
     Replaces the native AppSidebar with the Neoffice menu + a Calendars section:
     colour swatch (filled=visible / hollow=hidden), a shared indicator, and a
     per-calendar gear opening full settings (rename / colour / share / CalDAV /
     delete). Falls back to AppSidebar on failure. //// -->
<template>
	<!-- //// Neoffice — upstream's AppSidebar reads the calendars from the store and toggles them itself: it takes
	     //// no `calendars` / `visibleCalendars` any more, only the colour of a calendar and what the page relays. -->
	<AppSidebar
		v-if="failed"
		v-bind="$attrs"
		:calendar-color="calendarColor ?? fallbackCalendarColor"
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
//// Neoffice — upstream's calendars carry their own colour, as a hex (utils/calendars.ts): the palette's are named
//// back to draw them as the grid does.
import { CALENDAR_COLORS, calendarColor as colorOf } from '@/apps/calendar/utils/calendars'
//// Neoffice — the dates of the ERP, a group of read-only calendars of their own (maintenance#1428).
import { isErpCalendar, swatch } from '@/apps/calendar/utils/erpDates'

//// Neoffice — `inheritAttrs: false` + `v-bind="$attrs"` on the fallback: upstream's
//// AppSidebar has a mini-month and a list of today's events (month/year/day/events/
//// selectedEvent, @select-date, @select-event). This chrome does not read them itself,
//// but it must not swallow them either — they are relayed untouched so the fallback
//// keeps upstream's full behaviour.
defineOptions({ inheritAttrs: false })

const { calendars, visibleCalendars, erpScope, erpScoped, calendarColor } = defineProps<{
	/** The calendars as the page lists them (a row of `CalendarRow`, plus the ERP sources' `virtual` / `palette`). */
	calendars: any[]
	/** The names (`account|id`) of the calendars drawn: an array, or a Set as upstream's page holds them. */
	visibleCalendars: string[] | Set<string>
	//// Neoffice — whose dates the sources of the ERP show, and whether the person can choose (maintenance#1428).
	erpScope?: string
	erpScoped?: boolean
	/** The colour of a calendar, for the fallback AppSidebar's mini month; worked out from `calendars` if absent. */
	calendarColor?: (calendar: string) => string
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

const allCalendars = computed(() => calendars ?? [])
const fallbackCalendarColor = (name: string) => colorOf(allCalendars.value, name)

function openSettings(c: any) {
	editing.value = c
	showSettings.value = true
}

const isShown = (c: any): boolean => {
	const shown: string[] | Set<string> | undefined = visibleCalendars
	if (shown instanceof Set) return shown.has(c.name)
	if (Array.isArray(shown)) return shown.includes(c.name)
	return !!c.visible
}

//// Neoffice — the palette's hex goes back to its name, which `swatch` draws with the ink variable the grid uses;
//// a colour the owner set elsewhere (another hex) is drawn as it is. A calendar without a colour takes the one of
//// its position, as everywhere else.
const PALETTE_NAME_BY_HEX: Record<string, string> = Object.fromEntries(
	CALENDAR_COLORS.map(({ name, hex }) => [hex, name]),
)
const dotColor = (c: any): string => {
	const colour: string = c.color || colorOf(allCalendars.value, c.name)
	return swatch(PALETTE_NAME_BY_HEX[colour.toLowerCase()] ?? colour) || '#9BA3AF'
}

//// Neoffice — a calendar that lives in ANOTHER account is one that another person shared with this one: upstream's
//// `get_calendars_with_shared` brings them in beside the account's own, each row carrying its `account`
//// (maintenance#1579, upstream's own mechanism now). They are drawn like the person's own, with the shared mark and
//// whose they are; no gear, they are the owner's to rename, share or delete.
const isForeign = (c: any): boolean => !!c.account && !!store.accountId && c.account !== store.accountId
const ownerName = (c: any): string => {
	const accounts: { id: string; _name?: string }[] = store.userResource?.data?.all_accounts ?? []
	return accounts.find((a) => a.id === c.account)?._name || ''
}

//// Neoffice — the person's own calendars, then the dates of the ERP: read-only, switched like them, no gear and
//// nothing to change from here (maintenance#1428).
const ownCalendars = computed(() => allCalendars.value.filter((c) => !isErpCalendar(c)))
const erpItems = computed(() => [
	...allCalendars.value
		.filter((c) => isErpCalendar(c))
		.map((c) => ({
			label: c._name,
			color: swatch(c.palette) || '#9BA3AF',
			dim: !isShown(c),
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
				const foreign = isForeign(c)
				const owner = foreign ? ownerName(c) : ''
				return {
					label: c._name,
					//// Neoffice — dotColor(): a palette name drawn with the ink variable the grid uses (maintenance#1428).
					color: dotColor(c),
					dim: !isShown(c),
					//// Neoffice — the shared mark: this person shares the calendar (a count), or another person shared it
					//// with this one (its owner, from the account list upstream's sidebar reads it from).
					shared: sharedCount > 0 || foreign,
					sharedTitle: foreign
						? owner
							? __('Shared by {0}', [owner])
							: __('Shared')
						: !sharedCount
							? undefined
							: sharedCount === 1
								? __('Shared with 1 person')
								: __('Shared with {0} people', [sharedCount]),
					onGear: foreign ? undefined : () => openSettings(c),
					onClick: () => emit('update:visibleCalendars', c.name),
				}
			}),
			{ label: __('Add a calendar'), icon: 'lucide-plus', onClick: () => (showNew.value = true) },
			//// Neoffice — the agenda, read by Google, Outlook and Apple through a private address (maintenance#1428).
			{ label: __('Share your agenda'), icon: 'lucide-share-2', onClick: () => (showFeed.value = true) },
		],
	},
	//// Neoffice — then the dates of the ERP, when the site has any for this person (maintenance#1428).
	...(erpItems.value.length ? [{ label: __('Dates of Neoffice'), items: erpItems.value }] : []),
])
</script>

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
import CalendarSettingsModal from '@/apps/calendar/components/Modals/CalendarSettingsModal.vue'
import { userStore } from '@/apps/calendar/stores/user'

//// Neoffice — `inheritAttrs: false` + `v-bind="$attrs"` on the fallback: upstream's
//// AppSidebar grew a mini-month and an event list (month/year/day/view/events/
//// selectedEvent, @select-date, @select-event) after the merge of 31.08.2026. This
//// chrome does not read them itself, but it must not swallow them either — they are
//// relayed untouched so the fallback keeps upstream's full behaviour.
defineOptions({ inheritAttrs: false })

const { calendars, visibleCalendars } = defineProps<{
	calendars: any[]
	visibleCalendars: string[]
}>()
const emit = defineEmits(['update:visibleCalendars', 'reload'])

const router = useRouter()
const store = userStore()
const failed = ref(false)
const showNew = ref(false)
const showSettings = ref(false)
const editing = ref<any>(null)

const account = computed(() => store.accountId)
const surfaceApp = { name: 'calendar', title: 'Calendar', logo: calendarLogo }

function openSettings(c: any) {
	editing.value = c
	showSettings.value = true
}

const contextNav = computed(() => [
	{
		label: __('Calendars'),
		items: [
			// //// Neoffice: colour swatch (filled=visible, hollow=hidden), a
			// "shared" icon+tooltip, and a gear opening the calendar settings.
			// Click on the row toggles visibility. ////
			...calendars.map((c) => {
				const sharedCount = (c.share_with || []).length
				return {
					label: c._name,
					color: c.color || '#9BA3AF',
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
		],
	},
])
</script>

<!-- //// Neoffice: new file — Calendar flavor of the shared NeoCockpit chrome.
     Replaces the native AppSidebar (which had no cockpit, no "new calendar",
     no sharing) with the Neoffice menu + a Calendars section that toggles
     visibility and exposes creation. Falls back to AppSidebar on failure. //// -->
<template>
	<AppSidebar
		v-if="failed"
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
		<ShareCalendarModal v-model="showShare" :account="account" :calendars="calendars" />
	</template>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import calendarLogo from '@/assets/app-logos/calendar.svg'
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import AppSidebar from '@/apps/calendar/components/AppSidebar.vue'
import NewCalendarModal from '@/apps/calendar/components/Modals/NewCalendarModal.vue'
import ShareCalendarModal from '@/apps/calendar/components/Modals/ShareCalendarModal.vue'
import { userStore } from '@/apps/calendar/stores/user'

const { calendars, visibleCalendars } = defineProps<{
	calendars: any[]
	visibleCalendars: string[]
}>()
const emit = defineEmits(['update:visibleCalendars', 'reload'])

const router = useRouter()
const store = userStore()
const failed = ref(false)
const showNew = ref(false)
const showShare = ref(false)

const account = computed(() => store.accountId)
const surfaceApp = { name: 'calendar', title: 'Calendar', logo: calendarLogo }

const contextNav = computed(() => [
	{
		label: __('Calendars'),
		items: [
			// //// Neoffice: colour swatch (filled=visible, hollow=hidden) + a
			// "shared" icon with tooltip when the calendar is shared with others.
			// Click toggles visibility. ////
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
					onClick: () => emit('update:visibleCalendars', c.name),
				}
			}),
			{ label: __('New calendar'), icon: 'lucide-plus', onClick: () => (showNew.value = true) },
			{ label: __('Share a calendar'), icon: 'lucide-user-plus', onClick: () => (showShare.value = true) },
		],
	},
])
</script>

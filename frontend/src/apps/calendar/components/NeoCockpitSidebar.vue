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
	</template>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import calendarLogo from '@/assets/app-logos/calendar.svg'
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import AppSidebar from '@/apps/calendar/components/AppSidebar.vue'
import NewCalendarModal from '@/apps/calendar/components/Modals/NewCalendarModal.vue'
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

const account = computed(() => store.accountId)
const surfaceApp = { name: 'calendar', title: 'Calendar', logo: calendarLogo }

const contextNav = computed(() => [
	{
		label: __('Calendars'),
		items: [
			...calendars.map((c) => ({
				label: c._name,
				icon: visibleCalendars.includes(c.name) ? 'lucide-eye' : 'lucide-eye-off',
				onClick: () => emit('update:visibleCalendars', c.name),
			})),
			{ label: __('New calendar'), icon: 'lucide-plus', onClick: () => (showNew.value = true) },
		],
	},
])
</script>

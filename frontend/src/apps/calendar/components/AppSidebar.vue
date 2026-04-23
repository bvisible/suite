<script setup lang="ts">
import { computed, h, inject, ref } from 'vue'
import { Eye, EyeOff, LayoutGrid, LogOut, Settings } from 'lucide-vue-next'
import { Sidebar, createResource } from 'frappe-ui'

import { toTitleCase } from '@/utils/format'
import { sessionStore } from '@/stores/session'
import CalendarLogo from '@/components/Icons/CalendarLogo.vue'
import SettingsModal from '@/components/Modals/SettingsModal.vue'

const { calendars, visibleCalendars } = defineProps<{
	calendars: any[]
	visibleCalendars: string[]
}>()

const emit = defineEmits(['update:visibleCalendars'])

const { branding, logout } = sessionStore()

const user = inject('$user')

const title = computed(() =>
	branding.data?.brand_name && branding.data?.brand_name != 'Frappe'
		? branding.data.brand_name
		: 'Calendar',
)

const apps = createResource({
	url: 'mail.api.get_permitted_apps',
	cache: 'otherApps',
	auto: true,
	transform: (data) => data.filter((app) => app.name !== 'calendar_app'),
})

const showSettings = ref(false)

const menuItems = computed(() => [
	{
		icon: LayoutGrid,
		label: __('Apps'),
		submenu: apps.data?.map?.((app) => ({
			label: app.title,
			icon: app.logo,
			component: h(
				'a',
				{
					class: 'flex items-center gap-2 p-1.5 rounded hover:bg-surface-gray-2',
					href: app.route,
				},
				[
					h('img', { src: app.logo, class: 'size-6' }),
					h('span', { class: 'max-w-18 text-sm w-full truncate' }, app.title),
				],
			),
		})),
	},
	{
		icon: Settings,
		label: __('Settings'),
		onClick: () => (showSettings.value = true),
	},
	{
		icon: LogOut,
		label: __('Log Out'),
		onClick: logout.submit,
	},
])

const sidebarItems = computed(() => [
	{
		label: __('Calendars'),
		items:
			calendars.map((calendar) => ({
				label: calendar._name,
				icon: visibleCalendars.includes(calendar.name) ? Eye : EyeOff,
				onClick: () => emit('update:visibleCalendars', calendar.name),
			})) || [],
	},
])
</script>

<template>
	<Sidebar
		:header="{
			title,
			subtitle: toTitleCase(user.data?.full_name),
			menuItems,
			logo: branding.data?.brand_html || CalendarLogo,
		}"
		:sections="sidebarItems"
		:disable-collapse="true"
	/>
	<SettingsModal v-model="showSettings" />
</template>

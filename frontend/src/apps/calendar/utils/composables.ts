import { computed, ref } from 'vue'

import { userStore } from '@/apps/calendar/stores/user'

const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
const systemIsDark = ref(mediaQuery.matches)
mediaQuery.addEventListener('change', () => (systemIsDark.value = mediaQuery.matches))

export const useTheme = () => {
	const { userResource } = userStore()

	const dataTheme = computed(() => {
		const colorScheme = userResource.data?.color_scheme || 'System Default'
		if (colorScheme === 'System Default') return systemIsDark.value ? 'dark' : 'light'
		return colorScheme === 'Dark Mode' ? 'dark' : 'light'
	})

	return { dataTheme }
}

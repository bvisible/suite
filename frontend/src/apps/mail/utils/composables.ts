import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'

export const useScreenSize = () => {
	const size = reactive({ width: window.innerWidth, height: window.innerHeight })

	const isMobile = computed(() => size.width < 640)

	const onResize = () => {
		size.width = window.innerWidth
		size.height = window.innerHeight
	}

	onMounted(() => window.addEventListener('resize', onResize))

	onUnmounted(() => window.removeEventListener('resize', onResize))

	return { size, isMobile }
}

const isSidebarOpen = ref(false)

export const useSidebar = () => {
	const openSidebar = () => (isSidebarOpen.value = true)
	const closeSidebar = () => (isSidebarOpen.value = false)

	return { isSidebarOpen, openSidebar, closeSidebar }
}

export type Theme = 'light' | 'dark' | 'system'

const currentTheme = ref<Theme>('light')

export const useTheme = () => {
	const getSystemTheme = (): 'light' | 'dark' =>
		window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'

	const setTheme = (theme: Theme) => {
		currentTheme.value = theme
		document.documentElement.setAttribute(
			'data-theme',
			theme === 'system' ? getSystemTheme() : theme,
		)
		localStorage.setItem('theme', theme)
	}

	const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
	const handleSystemThemeChange = () => {
		if (currentTheme.value === 'system')
			document.documentElement.setAttribute('data-theme', getSystemTheme())
	}

	onMounted(() => {
		const storedTheme = localStorage.getItem('theme') as Theme | null
		setTheme(storedTheme || 'system')
		mediaQuery.addEventListener('change', handleSystemThemeChange)
	})
	onUnmounted(() => mediaQuery.removeEventListener('change', handleSystemThemeChange))

	const activeTheme = computed<'light' | 'dark'>(() =>
		currentTheme.value === 'system' ? getSystemTheme() : currentTheme.value,
	)

	return { currentTheme, setTheme, activeTheme }
}

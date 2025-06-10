import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'

export const useScreenSize = () => {
	const size = reactive({
		width: window.innerWidth,
		height: window.innerHeight,
	})

	const isMobile = computed(() => size.width < 640)

	const onResize = () => {
		size.width = window.innerWidth
		size.height = window.innerHeight
	}

	onMounted(() => window.addEventListener('resize', onResize))

	onUnmounted(() => window.removeEventListener('resize', onResize))

	return { size, isMobile }
}
// write a composable for detecting swipe gestures in mobile devices
export const useSwipe = () => {
	const swipe = reactive({
		initialX: null,
		initialY: null,
		currentX: null,
		currentY: null,
		diffX: null,
		diffY: null,
		absDiffX: null,
		absDiffY: null,
		direction: null,
	})

	const onTouchStart = (e) => {
		swipe.initialX = e.touches[0].clientX
		swipe.initialY = e.touches[0].clientY
		swipe.direction = null
		swipe.diffX = null
		swipe.diffY = null
		swipe.absDiffX = null
		swipe.absDiffY = null
	}

	const onTouchMove = (e) => {
		swipe.currentX = e.touches[0].clientX
		swipe.currentY = e.touches[0].clientY

		swipe.diffX = swipe.initialX - swipe.currentX
		swipe.diffY = swipe.initialY - swipe.currentY

		swipe.absDiffX = Math.abs(swipe.diffX)
		swipe.absDiffY = Math.abs(swipe.diffY)
	}

	const onTouchEnd = () => {
		const { diffX, diffY, absDiffX, absDiffY } = swipe
		if (absDiffX > absDiffY) {
			if (diffX > 0) {
				swipe.direction = 'left'
			} else {
				swipe.direction = 'right'
			}
		} else {
			if (diffY > 0) {
				swipe.direction = 'up'
			} else {
				swipe.direction = 'down'
			}
		}
	}

	onMounted(() => {
		window.addEventListener('touchstart', onTouchStart)
		window.addEventListener('touchend', onTouchEnd)
		window.addEventListener('touchmove', onTouchMove)
	})

	onUnmounted(() => {
		window.removeEventListener('touchstart', onTouchStart)
		window.removeEventListener('touchend', onTouchEnd)
		window.removeEventListener('touchmove', onTouchMove)
	})

	return swipe
}

const isSidebarOpen = ref(false)

export const useSidebar = () => {
	const openSidebar = () => (isSidebarOpen.value = true)
	const closeSidebar = () => (isSidebarOpen.value = false)

	return { isSidebarOpen, openSidebar, closeSidebar }
}

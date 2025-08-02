<template>
	<div class="absolute left-0 top-0 h-full w-full bg-black">
		<div
			ref="slideContainer"
			class="flex h-screen w-full items-center justify-center"
			:style="{
				clipPath: clipPath,
			}"
		>
			<Transition
				@before-enter="beforeSlideEnter"
				@enter="slideEnter"
				@before-leave="beforeSlideLeave"
				@leave="slideLeave"
			>
				<div
					:key="slideIndex"
					:style="slideStyles"
					@click="changeSlide(slideIndex + 1, false)"
				>
					<SlideElement
						v-for="element in slide.elements"
						:key="element.id"
						:element="element"
						:data-index="element.id"
						@click.stop
					/>
				</div>
			</Transition>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import SlideElement from '@/components/SlideElement.vue'

import {
	presentationId,
	presentation,
	inSlideShow,
	applyReverseTransition,
} from '@/stores/presentation'
import { slide, slideIndex, loadSlide } from '@/stores/slide'

const slideContainerRef = useTemplateRef('slideContainer')

const route = useRoute()
const router = useRouter()

const transition = ref('none')
const transform = ref('')
const opacity = ref(1)
const clipPath = ref('')

const slideCursor = ref('none')

const slideStyles = computed(() => {
	// scale slide to fit current screen size while maintaining 16:9 aspect ratio
	const screenWidth = window.screen.width
	const widthScale = screenWidth / 960

	return {
		width: '960px',
		height: '540px',
		backgroundColor: slide.value.background || 'white',
		cursor: slideCursor.value,
		transform: `${transform.value} scale(${widthScale})`,
		transition: transition.value,
		opacity: opacity.value,
	}
})

const transitionMap = {
	'Slide In': {
		beforeEnter: {
			transform: ['translateX(100%)', 'translateX(-100%)'],
			transition: 'none',
		},
		enter: {
			transform: 'translateX(0)',
			transition: `transform ${slide.value.transitionDuration}s ease-out`,
		},
		beforeLeave: {
			transition: 'none',
		},
		leave: {
			transform: ['translateX(100%)', 'translateX(-100%)'],
			transition: `transform ${slide.value.transitionDuration}s ease-out`,
		},
	},
	Fade: {
		beforeEnter: {
			opacity: 0,
		},
		enter: {
			transition: `opacity ${slide.value.transitionDuration}s`,
		},
		beforeLeave: {},
		leave: {
			transition: `opacity ${slide.value.transitionDuration}s`,
			opacity: 0,
		},
	},
}

const applyTransitionStyles = (hook) => {
	const styles = transitionMap[slide.value.transition][hook]

	let transformVal = styles.transform
	if (transformVal && Array.isArray(transformVal)) {
		transformVal = applyReverseTransition.value ? transformVal[1] : transformVal[0]
	}

	transform.value = transformVal || transform.value
	transition.value = styles.transition || transition.value
	opacity.value = styles.opacity
}

const beforeSlideEnter = (el) => {
	if (!slide.value.transition) return
	applyTransitionStyles('beforeEnter')
}

const slideEnter = (el, done) => {
	if (!slide.value.transition) return done()
	el.offsetWidth
	applyTransitionStyles('enter')
	done()
}

const beforeSlideLeave = (el) => {
	if (!slide.value.transition) return
	applyTransitionStyles('beforeLeave')
}

const slideLeave = (el, done) => {
	if (!slide.value.transition) return done()
	applyTransitionStyles('leave')
	done()
}

const resetCursorVisibility = () => {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 5000)
}

const handleFullScreenChange = () => {
	inSlideShow.value = document.fullscreenElement != null

	if (document.fullscreenElement) {
		slideContainerRef.value.addEventListener('mousemove', resetCursorVisibility)
	} else {
		slideContainerRef.value.removeEventListener('mousemove', resetCursorVisibility)
		router.replace({ name: 'PresentationEditor' })
	}
}

const handleKeyDown = (e) => {
	if (e.key == 'ArrowRight' || e.key == 'ArrowDown') {
		changeSlide(slideIndex.value + 1, false)
	} else if (e.key == 'ArrowLeft' || e.key == 'ArrowUp') {
		changeSlide(slideIndex.value - 1, false)
	}
}

const setClipPath = () => {
	const screenHeight = window.screen.height
	const scale = window.screen.width / 960
	const containerHeight = 540 * scale

	// divide remaining height by 2 to set inset on top and bottom
	const inset = (screenHeight - containerHeight) / 2

	clipPath.value = `inset(${inset}px 0px ${inset}px 0px)`
}

const initFullscreenMode = async () => {
	const container = slideContainerRef.value
	if (!container) return

	const fullscreenMethods = [
		container.requestFullscreen,
		container.webkitRequestFullscreen, // Safari
		container.msRequestFullscreen, // IE
		container.mozRequestFullScreen, // Firefox
	]

	const fullscreenMethod = fullscreenMethods.find((method) => method)

	if (fullscreenMethod) {
		fullscreenMethod.call(container).catch((e) => {
			router.replace({ name: 'PresentationEditor' })
		})
		inSlideShow.value = true

		setClipPath()
	}
}

const changeSlide = (index) => {
	if (index < 0 || index >= presentation.data.slides.length) return
	applyReverseTransition.value = index < slideIndex.value

	nextTick(() => {
		slideIndex.value = index
		loadSlide()
	})
}

const loadPresentation = async () => {
	if (presentation.fetched) return
	presentationId.value = route.params.presentationId
	await presentation.fetch()
	loadSlide()
}

onMounted(async () => {
	loadPresentation()
	initFullscreenMode()
	document.addEventListener('keydown', handleKeyDown)
	document.addEventListener('fullscreenchange', handleFullScreenChange)
})

onBeforeUnmount(() => {
	document.removeEventListener('keydown', handleKeyDown)
	document.removeEventListener('fullscreenchange', handleFullScreenChange)
})
</script>

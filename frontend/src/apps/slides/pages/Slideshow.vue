<template>
	<div class="bg-black fixed top-0 left-0 w-full h-full">
		<div
			ref="slideContainer"
			class="flex items-center justify-center w-full h-screen"
			:style="{
				clipPath: 'inset(45px 0 45px 0)',
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
					<component
						v-for="(element, index) in slide.elements"
						:key="index"
						:is="SlideElement"
						:element="element"
						:data-index="index"
					/>
				</div>
			</Transition>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import SlideElement from '@/components/SlideElement.vue'

import {
	presentationId,
	presentation,
	inSlideShow,
	applyReverseTransition,
} from '@/stores/presentation'
import { slide, slideIndex, changeSlide, loadSlide } from '@/stores/slide'

const slideContainerRef = useTemplateRef('slideContainer')

const route = useRoute()
const router = useRouter()

const transition = ref('none')
const transform = ref('')
const opacity = ref(1)

const slideCursor = ref('none')

const slideStyles = computed(() => {
	return {
		width: '960px',
		height: '540px',
		backgroundColor: slide.value.background || 'white',
		cursor: slideCursor.value,
		transform: 'scale(1.5)',
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
	opacity.value = styles.opacity || opacity.value
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
	}
}

watch(
	() => route.params.presentationId,
	async (id) => {
		if (!id) return
		presentationId.value = id
		await presentation.fetch()

		const currentSlide = presentation.data.slides[slideIndex.value]
		if (!currentSlide) return
		loadSlide()
	},
	{ immediate: true },
)

onMounted(async () => {
	await initFullscreenMode()
	document.addEventListener('keydown', handleKeyDown)
	document.addEventListener('fullscreenchange', handleFullScreenChange)
})

onBeforeUnmount(() => {
	document.removeEventListener('keydown', handleKeyDown)
	document.removeEventListener('fullscreenchange', handleFullScreenChange)
})
</script>

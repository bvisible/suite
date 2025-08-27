<template>
	<div class="absolute left-0 top-0 h-full w-full bg-black">
		<div
			ref="slideContainer"
			class="flex h-screen w-full items-center justify-center bg-white"
			:style="{
				clipPath: clipPath,
			}"
		>
			<div
				v-if="slideshowEnded"
				class="flex h-full w-full items-center justify-center bg-black"
			>
				<div class="flex gap-8">
					<Button
						label="Back"
						size="lg"
						:variant="'outline'"
						class="bg-transparent text-white opacity-70 transition-opacity duration-300 hover:opacity-100"
						@click="endSlideShow"
					>
						<template #prefix>
							<LucideChevronLeft class="size-4 stroke-[1.5]" />
						</template>
					</Button>
					<Button
						label="Replay"
						size="lg"
						class="opacity-90 transition-opacity duration-200 hover:opacity-100"
						@click="changeSlide(0)"
					>
						<template #prefix>
							<LucideRotateCcw class="size-4 stroke-[1.5]" />
						</template>
					</Button>
				</div>
			</div>

			<Transition
				v-else
				@before-enter="beforeSlideEnter"
				@enter="slideEnter"
				@before-leave="beforeSlideLeave"
				@leave="slideLeave"
			>
				<div :key="slideIndex" :style="slideStyles" @click="changeSlide(slideIndex + 1)">
					<SlideElement
						v-for="element in currentSlide?.elements"
						:key="`slideshow-${element.id}`"
						mode="slideshow"
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
import {
	ref,
	computed,
	watch,
	useTemplateRef,
	onMounted,
	nextTick,
	onActivated,
	onDeactivated,
} from 'vue'
import { useRouter } from 'vue-router'

import SlideElement from '@/components/SlideElement.vue'

import {
	presentationId,
	inSlideShow,
	applyReverseTransition,
	initPresentationDoc,
} from '@/stores/presentation'
import { slides, slideIndex, currentSlide } from '@/stores/slide'

const slideContainerRef = useTemplateRef('slideContainer')

const router = useRouter()

const props = defineProps({
	presentationId: {
		type: String,
		required: true,
	},
	activeSlideId: {
		type: Number,
		required: true,
	},
})

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
		backgroundColor: currentSlide.value?.background || '#ffffff',
		cursor: slideCursor.value,
		transform: `${transform.value} scale(${widthScale})`,
		transition: transition.value,
		opacity: opacity.value,
	}
})

const transitionMap = computed(() => {
	if (!currentSlide.value) return {}
	return {
		'Slide In': {
			beforeEnter: {
				transform: ['translateX(100%)', 'translateX(-100%)'],
				transition: 'none',
			},
			enter: {
				transform: 'translateX(0)',
				transition: `transform ${currentSlide.value.transitionDuration}s ease-out`,
			},
			beforeLeave: {
				transition: 'none',
			},
			leave: {
				transform: ['translateX(100%)', 'translateX(-100%)'],
				transition: `transform ${currentSlide.value.transitionDuration}s ease-out`,
			},
		},
		Fade: {
			beforeEnter: {
				opacity: 0,
			},
			enter: {
				transition: `opacity ${currentSlide.value.transitionDuration}s`,
			},
			beforeLeave: {},
			leave: {
				transition: `opacity ${currentSlide.value.transitionDuration}s`,
				opacity: 0,
			},
		},
	}
})

const applyTransitionStyles = (hook) => {
	const styles = transitionMap.value?.[currentSlide.value.transition]?.[hook]
	if (!styles) return

	let transformVal = styles.transform
	if (transformVal && Array.isArray(transformVal)) {
		transformVal = applyReverseTransition.value ? transformVal[1] : transformVal[0]
	}

	transform.value = transformVal || transform.value
	transition.value = styles.transition || transition.value
	opacity.value = styles.opacity
}

const beforeSlideEnter = (el) => {
	if (!currentSlide.value.transition) return
	applyTransitionStyles('beforeEnter')
}

const slideEnter = (el, done) => {
	if (!currentSlide.value.transition) return done()
	el.offsetWidth
	applyTransitionStyles('enter')
	done()
}

const beforeSlideLeave = (el) => {
	if (!currentSlide.value.transition) return
	applyTransitionStyles('beforeLeave')
}

const slideLeave = (el, done) => {
	if (!currentSlide.value.transition) return done()
	applyTransitionStyles('leave')
	done()
}

const resetCursorVisibility = () => {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 3000)
}

const handleFullScreenChange = () => {
	if (document.fullscreenElement) {
		slideContainerRef.value.addEventListener('mousemove', resetCursorVisibility)
		inSlideShow.value = true
	} else {
		slideContainerRef.value.removeEventListener('mousemove', resetCursorVisibility)
		endSlideShow()
	}
}

const performPreviousStep = () => {
	const videoEl = document.querySelector('video')
	if (videoEl && videoEl.currentTime > 0) {
		videoEl.currentTime = 0
		videoEl.pause()
		return
	}
	changeSlide(slideIndex.value - 1)
}

const performNextStep = () => {
	const videoEl = document.querySelector('video')
	if (videoEl && videoEl.currentTime == 0 && videoEl.paused) {
		videoEl.play()
		return
	}
	changeSlide(slideIndex.value + 1)
}

const handleKeyDown = (e) => {
	if (e.key == 'ArrowRight' || e.key == 'ArrowDown' || e.code == 'Space') {
		performNextStep()
	} else if (e.key == 'ArrowLeft' || e.key == 'ArrowUp') {
		performPreviousStep()
	} else if (e.key == 'F5') {
		e.preventDefault()
		changeSlide(0)
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

const slideshowEnded = computed(() => {
	return slideIndex.value >= slides.value.length
})

const endSlideShow = () => {
	inSlideShow.value = false
	const slide =
		slideIndex.value == slides.value.length ? slides.value.length : slideIndex.value + 1
	router.replace({
		name: 'PresentationEditor',
		params: { presentationId: props.presentationId },
		query: { slide: slide },
	})
}

const changeSlide = (index) => {
	if (index < 0) return
	if (index >= slides.value.length + 1) return endSlideShow()

	applyReverseTransition.value = index < slideIndex.value

	nextTick(() => {
		router.replace({
			name: 'Slideshow',
			params: { presentationId: props.presentationId },
			query: { slide: index + 1 },
		})
	})
}

const loadPresentation = async () => {
	if (slides.value.length) return
	initPresentationDoc(props.presentationId)
}

onActivated(() => {
	loadPresentation()
	initFullscreenMode()
	document.addEventListener('keydown', handleKeyDown)
	document.addEventListener('fullscreenchange', handleFullScreenChange)
})

onDeactivated(() => {
	document.removeEventListener('keydown', handleKeyDown)
	document.removeEventListener('fullscreenchange', handleFullScreenChange)
})

watch(
	() => props.activeSlideId,
	(index) => {
		slideIndex.value = parseInt(index) - 1
	},
	{ immediate: true },
)
</script>

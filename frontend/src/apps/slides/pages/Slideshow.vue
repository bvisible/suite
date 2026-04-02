<template>
	<div class="absolute left-0 top-0 h-full w-full bg-black">
		<div
			ref="slideContainer"
			class="flex h-screen w-full items-center justify-center"
			:style="slideContainerStyles"
		>
			<div
				v-if="showSlideshowEndScreen"
				class="flex h-full w-full items-center justify-center bg-black"
				@click="endSlideShow()"
			>
				<SlideshowEndScreen @restartSlideShow="changeSlideInSlideshow(0)" />
			</div>

			<div
				v-else-if="isMagicMoveApplied"
				:style="slideStyles"
				@click="changeSlideInSlideshow(slideIndex + 1)"
			>
				<FadeElementTransition
					:duration="parseFloat(prevSlide?.transitionDuration)"
					:skip="!prevSlide?.fadeUnmatchedElements"
				>
					<SlideElement
						v-for="element in currentSlide?.elements"
						:key="`slideshow-${getElementKey(element)}`"
						mode="slideshow"
						:element="element"
						:data-index="element.id"
						:transitionStyles="transitionStyles"
						:style="getElementTransitionStyles(element)"
						class="forward-transition"
					/>
				</FadeElementTransition>
			</div>

			<div v-else>
				<Transition
					@before-enter="beforeSlideEnter"
					@enter="slideEnter"
					@before-leave="beforeSlideLeave"
					@leave="slideLeave"
				>
					<div
						:key="slideIndex"
						:style="slideStyles"
						@click="changeSlideInSlideshow(slideIndex + 1)"
					>
						<SlideElement
							v-for="element in currentSlide?.elements"
							:key="`slideshow-${getElementKey(element)}`"
							mode="slideshow"
							:element="element"
							:data-index="element.id"
						/>
					</div>
				</Transition>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onActivated, onDeactivated, ref, useTemplateRef, watch, provide } from 'vue'
import { useRouter } from 'vue-router'

import SlideElement from '@/components/SlideElement.vue'
import SlideshowEndScreen from '@/components/SlideshowEndScreen.vue'
import FadeElementTransition from '@/components/FadeElementTransition.vue'

import {
	inSlideShowMode,
	showSlideshowEndScreen,
	endSlideShow,
	prefetchNextSlide,
	changeSlideInSlideshow,
} from '@/stores/slideshow'

import { applyReverseTransition, initPresentationDoc, inReadonlyMode } from '@/stores/presentation'
import { currentSlide, setSlideIndex, slideIndex, slides } from '@/stores/slide'
import { resetFocus } from '@/stores/element'

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

const getElementKey = (element) => {
	return element.refId || element.id
}

const slideCursor = ref('none')

const prevSlide = computed(() => {
	if (slideIndex.value == 0) return null
	return slides.value[slideIndex.value - 1]
})

const isMagicMoveApplied = computed(() => {
	if (applyReverseTransition.value) return false

	return (
		currentSlide.value?.transition == 'Magic Move' ||
		prevSlide.value?.transition == 'Magic Move'
	)
})

const slideStyles = computed(() => {
	// scale slide to fit screen width while maintaining 16:9 aspect ratio
	const widthScale = window.innerWidth / 960

	const baseStyles = {
		width: '960px',
		height: '540px',
		backgroundColor: currentSlide.value?.background || '#ffffff',
		cursor: slideCursor.value,
	}

	if (prevSlide.value?.transition == 'Magic Move') {
		return {
			...baseStyles,
			transform: `scale(${widthScale})`,
			opacity: 1,
			...transitionStyles.value,
		}
	}

	return {
		...baseStyles,
		transform: `${transform.value} scale(${widthScale})`,
		opacity: opacity.value,
		transition: transition.value,
	}
})

const getElementTransitionStyles = (element) => {
	const styles = transitionStyles.value

	// limit transition property in element container to dimensions and position only
	const transitionProperty = styles.transitionProperty == 'all' ? 'left, top, width, height' : ''

	return {
		...styles,
		transitionProperty: transitionProperty,
		'--transition-duration': styles.transitionDuration,
	}
}

const transitionStyles = computed(() => {
	if (applyReverseTransition.value) return {}

	const transitionProperty = prevSlide.value?.transition == 'Magic Move' ? 'all' : ''
	const transitionDuration = prevSlide.value?.transitionDuration

	return {
		transitionProperty: transitionProperty,
		transitionDuration: transitionDuration ? `${transitionDuration}s` : '0s',
		transitionTimingFunction: 'ease-in-out',
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
	if (slideCursor.value != 'none') return
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 9000)
}

const handleFullScreenChange = () => {
	if (document.fullscreenElement) {
		slideContainerRef.value.addEventListener('mousemove', resetCursorVisibility)
		inSlideShowMode.value = true
		setClipPath()
	} else {
		slideContainerRef.value.removeEventListener('mousemove', resetCursorVisibility)
		endSlideShow()
	}
}

const setClipPath = () => {
	const width = window.innerWidth
	const height = window.innerHeight
	const slideHeight = 540 * (width / 960)

	// divide remaining height by 2 to set inset on top and bottom
	const inset = Math.max(0, (height - slideHeight) / 2)

	clipPath.value = `inset(${inset}px 0px ${inset}px 0px)`
}

const slideContainerStyles = computed(() => {
	return {
		clipPath: clipPath.value,
		backgroundColor: currentSlide.value?.background || '#ffffff',
	}
})

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
	}
}

const loadPresentation = async () => {
	if (slides.value.length) return
	initPresentationDoc(props.presentationId)
}

onActivated(() => {
	resetFocus()
	loadPresentation()
	initFullscreenMode()
	document.addEventListener('fullscreenchange', handleFullScreenChange)

	// Initial prefetch of next slide
	setTimeout(() => {
		prefetchNextSlide()
	}, 500)
})

onDeactivated(() => {
	document.removeEventListener('fullscreenchange', handleFullScreenChange)
})

watch(
	() => props.activeSlideId,
	(index) => {
		setSlideIndex(index)
		// Prefetch next slide when current slide changes
		setTimeout(() => {
			prefetchNextSlide()
		}, 200)
	},
	{ immediate: true },
)

provide('inReadonlyMode', inReadonlyMode)
provide('inSlideShowMode', inSlideShowMode)
</script>

<style>
.forward-transition .textElement span {
	transition-property: all;
	transition-duration: var(--transition-duration);
	transition-timing-function: ease-in-out;
}
</style>

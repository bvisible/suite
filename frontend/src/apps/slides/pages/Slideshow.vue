<template>
	<div class="absolute left-0 top-0 h-full w-full bg-black">
		<div
			ref="slideContainer"
			class="flex h-screen w-full items-center justify-center"
			:style="slideContainerStyles"
		>
			<div
				v-if="slideshowEnded"
				class="flex h-full w-full items-center justify-center bg-black"
			>
				<SlideshowEndScreen
					@restartSlideShow="changeSlide(0)"
					@endSlideShow="endSlideShow"
				/>
			</div>

			<div
				v-else-if="isMagicMoveApplied"
				:style="slideStyles"
				@click="changeSlide(slideIndex + 1)"
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
						@click.stop
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
						@click="changeSlide(slideIndex + 1)"
					>
						<SlideElement
							v-for="element in currentSlide?.elements"
							:key="`slideshow-${getElementKey(element)}`"
							mode="slideshow"
							:element="element"
							:data-index="element.id"
							@click.stop
						/>
					</div>
				</Transition>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onActivated, onDeactivated, ref, useTemplateRef, watch } from 'vue'
import { useRouter } from 'vue-router'

import SlideElement from '@/components/SlideElement.vue'
import SlideshowEndScreen from '@/components/SlideshowEndScreen.vue'
import FadeElementTransition from '@/components/FadeElementTransition.vue'

import {
	applyReverseTransition,
	initPresentationDoc,
	inSlideShow,
	isPublicPresentation,
} from '@/stores/presentation'
import { currentSlide, slideIndex, slides } from '@/stores/slide'

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

const prefetchedAssets = ref(new Set())

const prefetchNextSlide = () => {
	const nextSlideIndex = slideIndex.value + 1
	if (nextSlideIndex >= slides.value.length) return

	const nextSlide = slides.value[nextSlideIndex]
	nextSlide?.elements?.forEach((element) => {
		if (element.type === 'image' && element.src) {
			prefetchAsset(element.src, 'image')
		} else if (element.type === 'video') {
			element.poster && prefetchAsset(element.poster, 'image')
		}
	})
}

const prefetchAsset = async (src, type) => {
	if (prefetchedAssets.value.has(src)) return
	prefetchedAssets.value.add(src)

	try {
		const url = buildAssetUrl(src, type)

		if (type === 'image') {
			// Use link prefetch for images
			const link = document.createElement('link')
			link.rel = 'preload'
			link.href = `/api/method/slides.api.file.get_media_file?src=${encodeURIComponent(url)}&public=${isPublicPresentation.value}`
			link.as = 'image'
			document.head.appendChild(link)
		}
	} catch (error) {
		console.warn('Failed to prefetch asset:', src, error)
	}
}

const buildAssetUrl = (src, type) => {
	if (src.startsWith('/private') || src.startsWith('/assets')) {
		return src
	}

	return `/private${src}`
}

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
	// scale slide to fit current screen size while maintaining 16:9 aspect ratio
	const screenWidth = window.screen.width
	const widthScale = screenWidth / 960

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
	const videoEls = document.querySelectorAll('video')

	for (const videoEl of videoEls) {
		if (videoEl && videoEl.currentTime == 0 && videoEl.paused) {
			videoEl.play()
			return
		}
	}
	changeSlide(slideIndex.value + 1)
}

const handleKeyDown = (e) => {
	if (e.key == 'ArrowRight' || e.key == 'ArrowDown' || e.code == 'Space' || e.key == 'PageDown') {
		performNextStep()
	} else if (e.key == 'ArrowLeft' || e.key == 'ArrowUp' || e.key == 'PageUp') {
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

		// Prefetch next slide assets after navigation
		setTimeout(() => {
			prefetchNextSlide()
		}, 100)
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

	// Initial prefetch of next slide
	setTimeout(() => {
		prefetchNextSlide()
	}, 500)
})

onDeactivated(() => {
	document.removeEventListener('keydown', handleKeyDown)
	document.removeEventListener('fullscreenchange', handleFullScreenChange)
})

watch(
	() => props.activeSlideId,
	(index) => {
		slideIndex.value = parseInt(index) - 1
		// Prefetch next slide when current slide changes
		setTimeout(() => {
			prefetchNextSlide()
		}, 200)
	},
	{ immediate: true },
)
</script>

<style>
.forward-transition .textElement span {
	transition-property: all;
	transition-duration: var(--transition-duration);
	transition-timing-function: ease-in-out;
}
</style>

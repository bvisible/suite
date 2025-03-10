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
					ref="target"
					:key="slideIndex"
					class="slide h-[540px] w-[960px]"
					:style="slideShowStyles"
					@click="changeSlide(slideIndex + 1)"
				>
					<component
						ref="element"
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
import { ref, computed, watch, useTemplateRef, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import SlideElement from '@/components/SlideElement.vue'

import { presentationId, presentation, inSlideShow } from '@/stores/presentation'
import { slide, slideIndex, changeSlide, loadSlide } from '@/stores/slide'

const slideContainerRef = useTemplateRef('slideContainer')

const route = useRoute()
const router = useRouter()

const transition = ref('none')
const transitionTransform = ref('')
const opacity = ref(1)

const slideCursor = ref('none')

const slideShowStyles = computed(() => {
	return {
		backgroundColor: slide.value.background || 'white',
		cursor: slideCursor.value,
		transformOrigin: 'center',
		transform: `matrix(1.5, 0, 0, 1.5, 0, 0) ${transitionTransform.value}`,
		transition: transition.value,
		opacity: opacity.value,
	}
})

const beforeSlideEnter = (el) => {
	if (!slide.value.transition) return
	if (slide.value.transition == 'Slide In') {
		transitionTransform.value = applyReverseTransition.value
			? 'translateX(-100%)'
			: 'translateX(100%)'
		transition.value = 'none'
	} else if (slide.value.transition == 'Fade') {
		opacity.value = 0
	}
}

const slideEnter = (el, done) => {
	if (!slide.value.transition) return done()
	el.offsetWidth
	if (slide.value.transition == 'Slide In') {
		transition.value = `transform ${slide.value.transitionDuration}s ease-out`
		transitionTransform.value = 'translateX(0)'
	} else if (slide.value.transition == 'Fade') {
		transition.value = `opacity ${slide.value.transitionDuration}s`
		opacity.value = 1
	}
	done()
}

const beforeSlideLeave = (el) => {
	if (!slide.value.transition) return
	if (slide.value.transition == 'Slide In') {
		transition.value = 'none'
	} else if (slide.value.transition == 'Fade') {
		opacity.value = 1
	}
}

const slideLeave = (el, done) => {
	if (!slide.value.transition) return done()
	if (slide.value.transition == 'Slide In') {
		transitionTransform.value = applyReverseTransition.value
			? 'translateX(100%)'
			: 'translateX(-100%)'
		transition.value = `transform ${slide.value.transitionDuration}s ease-out`
	} else if (slide.value.transition == 'Fade') {
		el.offsetWidth
		transition.value = `opacity ${slide.value.transitionDuration}s`
		opacity.value = 0
	}
	done()
}

watch(
	() => presentation.data,
	() => {
		const currentSlide = presentation.data?.slides[slideIndex.value]
		if (!currentSlide) return
		loadSlide(currentSlide)
	},
	{ immediate: true },
)

watch(
	() => route.params.presentationId,
	async (id) => {
		if (!id) return
		presentationId.value = id
		await presentation.fetch()
	},
	{ immediate: true },
)

const startSlideShow = async () => {
	const elem = slideContainerRef.value

	if (elem.requestFullscreen) {
		elem.requestFullscreen()
	} else if (elem.webkitRequestFullscreen) {
		elem.webkitRequestFullscreen()
	} else if (elem.msRequestFullscreen) {
		elem.msRequestFullscreen()
	}
}

const resetCursorVisibility = () => {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 5000)
}

const handleFullScreenChange = async () => {
	if (document.fullscreenElement) {
		slideContainerRef.value.addEventListener('mousemove', resetCursorVisibility)
	} else {
		router.replace({ name: 'Presentation', query: null })
		slideContainerRef.value.removeEventListener('mousemove', resetCursorVisibility)
	}
}

const handleKeyDown = (e) => {
	if (e.key == 'ArrowRight' || e.key == 'ArrowDown') {
		changeSlide(slideIndex.value + 1)
	} else if (e.key == 'ArrowLeft' || e.key == 'ArrowUp') {
		changeSlide(slideIndex.value - 1)
	}
}

onMounted(async () => {
	const present = route.query.present
	if (present) {
		present && (await startSlideShow())
		inSlideShow.value = present
	}
	document.addEventListener('keydown', handleKeyDown)
	document.addEventListener('fullscreenchange', handleFullScreenChange)
})
</script>

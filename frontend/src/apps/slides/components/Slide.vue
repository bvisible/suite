<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div v-if="inSlideShow">
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
	<div v-else ref="target" :style="targetStyles">
		<div
			class="slide h-[540px] w-[960px] shadow-2xl"
			:class="!activeElementIds.length ? 'shadow-gray-400' : 'shadow-gray-300'"
			:style="slideStyles"
		>
			<SelectionBox @selectSlide="selectSlide" />

			<ElementAlignmentGuides ref="guides" v-if="showGuides" :scale="scale" />

			<component
				ref="element"
				v-for="(element, index) in slide.elements"
				:key="index"
				:is="SlideElement"
				:element="element"
				:data-index="index"
			/>
		</div>

		<!-- Slide Actions -->
		<div class="fixed -bottom-12 right-0 cursor-pointer p-3 flex items-center gap-4">
			<Trash size="14" class="text-gray-800 stroke-[1.5]" @click="deleteSlide" />
			<Copy size="14" class="text-gray-800 stroke-[1.5]" @click="duplicateSlide" />
			<SquarePlus
				size="14"
				class="text-gray-800 stroke-[1.5]"
				@click="insertSlide(slideIndex + 1)"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useElementBounding } from '@vueuse/core'

import { Trash, Copy, SquarePlus } from 'lucide-vue-next'
import SlideElement from '@/components/SlideElement.vue'
import ElementAlignmentGuides from '@/components/ElementAlignmentGuides.vue'
import SelectionBox from './SelectionBox.vue'

import { presentation, inSlideShow, applyReverseTransition } from '@/stores/presentation'
import {
	slideIndex,
	slideFocus,
	slide,
	insertSlide,
	deleteSlide,
	duplicateSlide,
	slideRect,
	changeSlide,
	loadSlide,
	getSlideThumbnail,
} from '@/stores/slide'
import {
	activePosition,
	activeDimensions,
	activeElements,
	activeElementIds,
	focusElementId,
	resetFocus,
} from '@/stores/element'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'
import { usePanAndZoom } from '@/utils/zoom'

const router = useRouter()

const props = defineProps({
	containerRef: Object,
})

const targetRef = useTemplateRef('target')
const guides = useTemplateRef('guides')

slideRect.value = useElementBounding(targetRef)

const { isDragging, dragTarget, movement } = useDragAndDrop()
const { isResizing, resizeTarget, resizeMode } = useResizer(activePosition, activeDimensions)
const { isPanningOrZooming, allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(
	props.containerRef,
	targetRef,
)

const slideCursor = ref('none')
const transition = ref('none')
const transitionTransform = ref('')
const opacity = ref(1)

const showGuides = computed(() => activeElementIds.value.length && !isPanningOrZooming.value)

const scale = computed(() => {
	const matrix = transform.value.match(/matrix\((.+)\)/)
	if (!matrix) return 1
	return parseFloat(matrix[1].split(', ')[0])
})

const slideShowStyles = computed(() => ({
	backgroundColor: slide.value.background || 'white',
	cursor: slideCursor.value,
	transformOrigin: 'center',
	transform: `matrix(1.5, 0, 0, 1.5, 0, 0) ${transitionTransform.value}`,
	transition: transition.value,
	opacity: opacity.value,
}))

const targetStyles = computed(() => ({
	transformOrigin: transformOrigin.value,
	transform: transform.value,
}))

const slideStyles = computed(() => ({
	backgroundColor: slide.value.background || 'white',
	cursor: isDragging.value ? 'move' : 'default',
	'--showEdgeOverlay': !activeElementIds.value.length ? 'block' : 'none',
}))

const selectSlide = (e) => {
	if (!e.target.classList.contains('slide')) return
	e.preventDefault()
	e.stopPropagation()
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	if (focusElementId.value) {
		slide.value.elements[focusElementId.value].content = document.querySelector(
			`[data-index="${focusElementId.value}"]`,
		).innerText
	}
	resetFocus()
	slideFocus.value = true
}

const addDragAndResize = () => {
	let el = document.querySelector('.groupDiv')
	if (!el) return
	nextTick(() => {
		dragTarget.value = el
	})
	if (activeElementIds.value.length == 1) {
		resizeTarget.value = document.querySelector(`[data-index="${activeElementIds.value[0]}"]`)
		resizeMode.value = activeElements.value[0].type == 'text' ? 'width' : 'both'
	}
}

const removeDragAndResize = (val) => {
	activePosition.value = null
	activeDimensions.value = null
	dragTarget.value = null
	resizeTarget.value = null
}

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

const resetCursorVisibility = () => {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 3000)
}

const handleScreenChange = async () => {
	if (document.fullscreenElement) {
		allowPanAndZoom.value = false
		props.containerRef.addEventListener('mousemove', resetCursorVisibility)
	} else {
		await router.replace({ query: null })
		allowPanAndZoom.value = true
		props.containerRef.removeEventListener('mousemove', resetCursorVisibility)
	}
}

watch(
	() => activeElementIds.value,
	(newVal, oldVal) => {
		if (newVal.length) {
			addDragAndResize()
		} else if (oldVal) {
			removeDragAndResize(oldVal)

			nextTick(async () => {
				slide.value.thumbnail = await getSlideThumbnail()
			})
		}
	},
	{ immediate: true },
)

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
	() => movement.value,
	() => {
		if (!movement.value || !activePosition.value) return

		const { x, y } = movement.value

		guides.value.updateElementPosition(x, y)

		const groupDiv = document.querySelector('.groupDiv')
		if (groupDiv) {
			const groupLeft = activePosition.value.left
			const groupTop = activePosition.value.top

			groupDiv.style.left = `${groupLeft}px`
			groupDiv.style.top = `${groupTop}px`
		}
	},
	{ immediate: true },
)

watch(
	() => activeDimensions.value,
	(dimensions) => {
		if (!dimensions) return
		let element = slide.value.elements[activeElementIds.value[0]]
		if (element && dimensions.width != element.width) {
			const newWidth = dimensions.width / scale.value
			element.width = newWidth
		}
	},
	{ immediate: true },
)

watch(
	() => dragTarget.value,
	() => {
		if (!dragTarget.value) return
		let rect = dragTarget.value.getBoundingClientRect()
		activePosition.value = {
			left: rect.left - slideRect.value.left,
			top: rect.top - slideRect.value.top,
		}
	},
	{ immediate: true },
)

onMounted(() => {
	document.addEventListener('fullscreenchange', handleScreenChange)
})

onBeforeUnmount(() => {
	document.removeEventListener('fullscreenchange', handleScreenChange)
})

defineExpose({
	guides,
})
</script>

<style src="../assets/styles/resizer.css"></style>

<style>
.slide::after {
	content: '';
	display: var(--showEdgeOverlay, none);
	width: 100%;
	height: 100%;
	position: absolute;
	background: transparent;
	pointer-events: none;
	box-shadow: 0 0 5000px 500px rgba(255, 255, 255, 0.6);
}
</style>

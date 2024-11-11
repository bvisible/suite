<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		class="slideContainer flex items-center justify-center"
		:class="inSlideShow ? 'bg-black-900' : ''"
		:style="{
			width: '960px',
			height: '540px',
		}"
	>
		<div
			ref="target"
			class="slide h-[540px] w-[960px] drop-shadow-xl"
			:style="{
				backgroundColor:
					(presentation.data &&
						presentation.data.slides[activeSlideIndex - 1]?.background) ||
					'white',
			}"
			:class="activeElement?.type == 'slide' ? 'ring-[1px] ring-gray-200' : ''"
			@click="handleSlideClick"
		>
			<div v-if="activeSlideElements">
				<TransitionGroup
					v-if="inSlideShow"
					tag="div"
					@enter="handleSlideEnter"
					@leave="handleSlideLeave"
				>
					<component
						v-for="(element, index) in activeSlideElements"
						:key="index"
						:is="SlideElement"
						:element="element"
					/>
				</TransitionGroup>
				<component
					v-else
					ref="element"
					v-for="(element, index) in activeSlideElements"
					:key="index"
					:is="SlideElement"
					:element="element"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	onMounted,
	ref,
	unref,
	useTemplateRef,
	watch,
	onBeforeUnmount,
	TransitionGroup,
	nextTick,
	computed,
	provide,
} from 'vue'
import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'

import SlideElement from '@/components/SlideElement.vue'

import {
	activeElement,
	focusedElement,
	activeSlideIndex,
	presentation,
	activeSlideElements,
	inSlideShow,
} from '@/stores/slide'
import { isEqual } from 'lodash'
import html2canvas from 'html2canvas'

const targetRef = useTemplateRef('target')

const position = ref(null)
const dimensions = ref(null)

const { isDragging, dragTarget } = useDragAndDrop(position)
const { isResizing, resizeTarget, resizeMode } = useResizer(position, dimensions)

const selectSlide = (e) => {
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	e.preventDefault()
	e.stopPropagation()
	activeElement.value = {
		type: 'slide',
	}
	focusedElement.value = null
	removeDragAndResize()
}

const handleSlideClick = (e) => {
	if (e.target != targetRef.value) return
	if (inSlideShow.value) {
		activeSlideIndex.value += 1
		return
	} else selectSlide(e)
}

const setActiveElement = (e, element) => {
	if (inSlideShow.value) return
	if (activeElement.value == element && isResizing.value) {
		isResizing.value = false
		return
	}
	e.preventDefault()
	e.stopPropagation()

	activeElement.value = element
	focusedElement.value = null
	addDragAndResize(e.target)
}

const addDragAndResize = (el) => {
	let rect = el.getBoundingClientRect()
	position.value = {
		top: rect.top,
		left: rect.left,
	}
	dimensions.value = {
		width: rect.width,
	}

	dragTarget.value = el
	if (activeElement.value.type == 'text') {
		resizeTarget.value = el
		resizeMode.value = 'width'
	} else {
		resizeTarget.value = el.parentElement
		resizeMode.value = 'both'
	}
}

const removeDragAndResize = () => {
	position.value = null
	dimensions.value = null
	dragTarget.value = null
	resizeTarget.value = null
}

const duplicateElement = (e) => {
	e.preventDefault()
	if (activeElement.value) {
		let newElement = JSON.parse(JSON.stringify(activeElement.value))
		newElement.top += 10
		newElement.left += 10
		activeSlideElements.value.push(newElement)
		activeElement.value = newElement
		nextTick(() => {
			let el = document.querySelector('.active')
			addDragAndResize(el)
		})
	}
}

const handleKeyDown = (event) => {
	if (document.activeElement.tagName == 'INPUT') return
	if (['Delete', 'Backspace'].includes(event.key) && !focusedElement.value) {
		if (activeElement.value) {
			activeSlideElements.value = activeSlideElements.value.filter(
				(el) => !isEqual(el, activeElement.value),
			)
			activeElement.value = null
		}
	} else if (event.key == 'd' && event.metaKey) duplicateElement(event)
}

const updateSlideThumbnail = (index) => {
	html2canvas(targetRef.value).then((canvas) => {
		let img = canvas.toDataURL('image/png')
		presentation.data.slides[index].thumbnail = img
	})
}

watch(
	() => activeSlideIndex.value,
	(new_val, old_val) => {
		if (!presentation.data) return
		if (old_val && presentation.data.slides[old_val - 1]) {
			presentation.data.slides[old_val - 1].elements = JSON.stringify(
				activeSlideElements.value,
			)
			updateSlideThumbnail(old_val - 1)
		}
		if (presentation.data.slides[new_val - 1]) {
			if (presentation.data.slides[new_val - 1].elements)
				activeSlideElements.value = JSON.parse(
					presentation.data.slides[new_val - 1].elements,
				)
			else activeSlideElements.value = []
		}
	},
	{ immediate: true },
)

watch(
	() => activeElement.value,
	() => {
		updateSlideThumbnail(activeSlideIndex.value - 1)
	},
)

watch(
	() => presentation.data,
	() => {
		if (!presentation.data?.slides[activeSlideIndex.value - 1]?.elements) return
		activeSlideElements.value = JSON.parse(
			presentation.data.slides[activeSlideIndex.value - 1].elements,
		)
	},
	{ immediate: true },
)

onMounted(() => {
	window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
	window.removeEventListener('keydown', handleKeyDown)
})

const handleSlideEnter = (el, done) => {
	el.style.opacity = 0
	nextTick(() => {
		el.style.transition = 'opacity 1s'
		el.style.opacity = 1
	})
}

const handleSlideLeave = (el, done) => {
	el.style.opacity = 1
	nextTick(() => {
		el.style.transition = 'opacity 1s'
		el.style.opacity = 0
	})
}

watch(
	() => position.value,
	() => {
		if (!position.value) return
		let container = targetRef.value.getBoundingClientRect()
		let currentScale = container.width / 960
		activeElement.value.left = (position.value.left - container.left) / currentScale
		activeElement.value.top = (position.value.top - container.top) / currentScale
	},
	{ immediate: true },
)

watch(
	() => dimensions.value,
	() => {
		if (!dimensions.value) return
		if (activeElement.value && dimensions.value.width != activeElement.value.width) {
			let currentScale = targetRef.value.getBoundingClientRect().width / 960
			activeElement.value.width = dimensions.value.width / currentScale
		}
	},
	{ immediate: true },
)

provide('setActiveElement', setActiveElement)
provide('removeDragAndResize', removeDragAndResize)
provide('isDragging', isDragging)

defineExpose({
	targetRef,
})
</script>

<style src="../assets/styles/resizer.css"></style>

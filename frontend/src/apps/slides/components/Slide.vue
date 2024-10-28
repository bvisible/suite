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
			@click="selectSlide"
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
						@click="selectElement($event, element)"
						class="focus:outline-none"
						:class="isEqual(activeElement, element) ? 'ring-[1.5px] ring-blue-400' : ''"
					/>
				</TransitionGroup>
				<component
					v-else
					ref="element"
					v-for="(element, index) in activeSlideElements"
					:key="index"
					:is="SlideElement"
					:element="element"
					@click="selectElement($event, element)"
					class="focus:outline-none"
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
} from 'vue'
import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'

import SlideElement from '@/components/SlideElement.vue'

import {
	activeElement,
	activeSlideIndex,
	presentation,
	activeSlideElements,
	inSlideShow,
} from '@/stores/slide'
import { isEqual } from 'lodash'
import html2canvas from 'html2canvas'

const targetRef = useTemplateRef('target')

defineExpose({
	targetRef,
})

const position = ref(null)
const dimensions = ref(null)

const { dragTarget } = useDragAndDrop(position)
const { isResizing, resizeTarget, resizeMode } = useResizer(position, dimensions)

const selectSlide = (e) => {
	if (inSlideShow.value || e.target != targetRef.value) return
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	e.preventDefault()
	e.stopPropagation()
	activeElement.value = {
		type: 'slide',
	}
	dragTarget.value = null
	resizeTarget.value = null
}

const selectElement = (e, element) => {
	if (inSlideShow.value) return
	if (activeElement.value == element && isResizing.value) {
		isResizing.value = false
		return
	}
	e.preventDefault()
	e.stopPropagation()

	activeElement.value = element
	addDragAndResize(e.target)
}

const addDragAndResize = (el) => {
	let rect = el.getBoundingClientRect()
	let container = targetRef.value.getBoundingClientRect()

	position.value = { left: rect.left - container.left, top: rect.top - container.top }
	dimensions.value = { width: rect.width }

	dragTarget.value = el
	if (activeElement.value.type == 'text') {
		resizeTarget.value = el
		resizeMode.value = 'width'
	} else {
		resizeTarget.value = el.parentElement
		resizeMode.value = 'both'
	}
}

const handleKeyDown = (event) => {
	if (document.activeElement.tagName == 'INPUT') return
	if (['Delete', 'Backspace'].includes(event.key) && !activeElement.value.isContentEditable) {
		if (activeElement.value) {
			activeSlideElements.value = activeSlideElements.value.filter(
				(el) => !isEqual(el, activeElement.value),
			)
			activeElement.value = null
		}
	}
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
		if (
			activeElement.value &&
			(position.value.top != activeElement.value.top ||
				position.value.left != activeElement.value.left)
		) {
			let currentScale = targetRef.value.getBoundingClientRect().width / 960
			activeElement.value.top = position.value.top / currentScale
			activeElement.value.left = position.value.left / currentScale
		}
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
</script>

<style src="../assets/styles/resizer.css"></style>

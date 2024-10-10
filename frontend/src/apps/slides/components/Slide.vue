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
			@dblclick="selectSlide"
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
						:is="getDynamicComponent(element.type)"
						:element="element"
						@click="selectElement($event, element)"
						class="focus:outline-none"
						:class="isEqual(activeElement, element) ? 'ring-[1.5px] ring-blue-400' : ''"
					/>
				</TransitionGroup>
				<component
					v-else
					v-for="(element, index) in activeSlideElements"
					:key="index"
					:is="getDynamicComponent(element.type)"
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
} from 'vue'
import { useDragAndDrop } from '@/utils/drag'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'

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

const selectSlide = (e) => {
	if (inSlideShow.value) return
	e.preventDefault()
	e.stopPropagation()
	if (e.target != targetRef.value) return
	activeElement.value = {
		type: 'slide',
	}
}

const selectElement = (e, element) => {
	if (inSlideShow.value) return
	e.stopPropagation()
	if (activeElement.value == element) return

	activeElement.value = element
	makeElementDraggable(e.target, element)
}

const makeElementDraggable = (el, element) => {
	useDragAndDrop(el, element)
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

const getDynamicComponent = (type) => {
	switch (type) {
		case 'image':
			return ImageElement
		case 'video':
			return VideoElement
		default:
			return TextElement
	}
}

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
</script>

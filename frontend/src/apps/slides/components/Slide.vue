<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		ref="slideContainer"
		class="slideContainer flex items-center justify-center"
		:class="inSlideShow ? 'bg-black-900' : ''"
		:style="{
			width: '960px',
			height: '540px',
			cursor: inSlideShow ? slideCursor : 'default',
		}"
	>
		<div
			ref="target"
			class="h-[540px] w-[960px] drop-shadow-xl"
			:style="slideStyles"
			:class="activeElement?.type == 'slide' ? 'ring-[1px] ring-gray-200' : ''"
			@click="handleSlideClick"
		>
			<div
				v-show="isDragging && showVerticalCenter"
				class="absolute left-1/2 h-full w-[1px] -translate-x-1/2 bg-blue-400"
			></div>

			<div
				v-show="isDragging && showHorizontalCenter"
				class="absolute top-1/2 h-[1px] w-full -translate-y-1/2 bg-blue-400"
			></div>

			<div v-show="diffLeft < 10" :style="leftGuideStyles"></div>
			<div v-show="diffRight < 10" :style="rightGuideStyles"></div>
			<div v-show="diffTop < 10" :style="topGuideStyles"></div>
			<div v-show="diffBottom < 10" :style="bottomGuideStyles"></div>

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
					:data-index="index"
					:currentPairedDataIndex="currentPairedDataIndex"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	onMounted,
	ref,
	useTemplateRef,
	watch,
	TransitionGroup,
	nextTick,
	computed,
	provide,
	onBeforeUnmount,
} from 'vue'
import { useElementBounding } from '@vueuse/core'

import SlideElement from '@/components/SlideElement.vue'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'

import {
	currentDataIndex,
	activeElement,
	focusedElement,
	activeSlideIndex,
	presentation,
	activeSlideElements,
	inSlideShow,
} from '@/stores/slide'
import html2canvas from 'html2canvas'

const zoom = defineModel('zoom')

const slideContainerRef = useTemplateRef('slideContainer')
const targetRef = useTemplateRef('target')

const { transform, transformOrigin, allowPanAndZoom } = zoom.value

const slideCursor = ref('auto')
const position = ref(null)
const dimensions = ref(null)

const { isDragging, dragTarget } = useDragAndDrop(position)
const { isResizing, resizeTarget, resizeMode } = useResizer(position, dimensions)

const slideStyles = computed(() => {
	if (!presentation.data) return
	return {
		backgroundColor: presentation.data.slides[activeSlideIndex.value]?.background || 'white',
		transform: transform.value,
		transformOrigin: transformOrigin.value,
	}
})

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	activeElement.value = {
		type: 'slide',
	}
	if (focusedElement.value) {
		focusedElement.value.content = document.querySelector(
			`[data-index="${currentDataIndex.value}"]`,
		).innerText
		focusedElement.value = null
	}
	currentDataIndex.value = null
}

const handleSlideClick = (e) => {
	e.stopPropagation()
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

	if (focusedElement.value) {
		focusedElement.value.content = document.querySelector(
			`[data-index="${currentDataIndex.value}"]`,
		).innerText
		focusedElement.value = null
	}

	activeElement.value = element
	currentDataIndex.value = activeSlideElements.value.indexOf(element)
}

const addDragAndResize = () => {
	let el = document.querySelector(`[data-index="${currentDataIndex.value}"]`)
	if (!el || !activeElement.value) return
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
		currentDataIndex.value = activeSlideElements.value.indexOf(newElement)
	}
}

const handleKeyDown = (event) => {
	if (document.activeElement.tagName == 'INPUT') return
	if (['Delete', 'Backspace'].includes(event.key) && !focusedElement.value) {
		if (activeElement.value) {
			activeSlideElements.value.splice(currentDataIndex.value, 1)
			activeElement.value = null
		}
	} else if (event.key == 'd' && event.metaKey) duplicateElement(event)
}

const updateSlideThumbnail = (index) => {
	if (!targetRef.value) return
	html2canvas(targetRef.value).then((canvas) => {
		let img = canvas.toDataURL('image/png')
		presentation.data.slides[index].thumbnail = img
	})
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

function resetCursorVisibility() {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 2000)
}

const handleScreenChange = () => {
	inSlideShow.value = document.fullscreenElement

	if (document.fullscreenElement) {
		activeElement.value = null
		transformOrigin.value = ''
		transform.value = 'scale(1.5, 1.5)'
		allowPanAndZoom.value = false
		targetRef.value.addEventListener('mousemove', resetCursorVisibility)
	} else {
		transform.value = ''
		transformOrigin.value = '0 0'
		allowPanAndZoom.value = true
		targetRef.value.removeEventListener('mousemove', resetCursorVisibility)
	}
}

watch(
	() => activeSlideIndex.value,
	(new_val, old_val) => {
		if (!presentation.data) return
		activeElement.value = null
		focusedElement.value = null
		currentDataIndex.value = null
		if (presentation.data.slides[old_val]) {
			presentation.data.slides[old_val].elements = JSON.stringify(activeSlideElements.value)
			updateSlideThumbnail(old_val)
		}
		if (presentation.data.slides[new_val]) {
			if (presentation.data.slides[new_val].elements)
				activeSlideElements.value = JSON.parse(presentation.data.slides[new_val].elements)
			else activeSlideElements.value = []
		}
	},
	{ immediate: true },
)

watch(
	() => activeElement.value,
	() => {
		removeDragAndResize()
		addDragAndResize()
	},
	{ immediate: true },
)

watch(
	() => presentation.data,
	() => {
		if (!presentation.data?.slides[activeSlideIndex.value]?.elements) return
		activeSlideElements.value = JSON.parse(
			presentation.data.slides[activeSlideIndex.value].elements,
		)
	},
	{ immediate: true },
)

const activeDiv = computed(() => {
	return document.querySelector(`[data-index="${currentDataIndex.value}"]`)
})

const pairedDiv = computed(() => {
	return document.querySelector(`[data-index="${currentPairedDataIndex.value}"]`)
})

const currentPairedDataIndex = computed(() => {
	if (!activeElement.value) return
	let i = null
	activeSlideElements.value.forEach((element, index) => {
		if (index == currentDataIndex.value) return
		let diffLeft = Math.abs(element.left - activeElement.value.left)
		let diffRight = Math.abs(
			element.left + element.width - activeElement.value.left - activeElement.value.width,
		)
		let diffTop = Math.abs(element.top - activeElement.value.top)
		let elementDiv = document.querySelector(`[data-index="${index}"]`).getBoundingClientRect()
		let diffBottom = Math.abs(
			element.top + elementDiv.height - activeElement.value.top - activeRect.height.value,
		)
		if (diffLeft < 10 || diffRight < 10 || diffTop < 10 || diffBottom < 10) i = index
	})
	return i
})

const slideRect = useElementBounding(targetRef)
const activeRect = useElementBounding(activeDiv)
const pairedRect = useElementBounding(pairedDiv)

const pairElement = computed(() => {
	if (!isDragging.value) return
	return activeSlideElements.value[currentPairedDataIndex.value]
})

const snapToPairElement = () => {
	if (!pairElement.value) return
	if (diffLeft.value < 10) {
		activeElement.value.left = pairElement.value.left
	}
	if (diffRight.value < 10) {
		activeElement.value.left =
			pairElement.value.left + pairElement.value.width - activeElement.value.width
	}
	if (diffTop.value < 10) {
		activeElement.value.top = pairElement.value.top
	}
	if (diffBottom.value < 10) {
		activeElement.value.top =
			pairElement.value.top + pairedRect.height.value - activeRect.height.value
	}
}

const showVerticalCenter = ref(false)
const showHorizontalCenter = ref(false)

const diffLeft = computed(() => {
	if (!pairElement.value) return
	return Math.abs(pairElement.value.left - activeElement.value.left)
})

const diffRight = computed(() => {
	if (!pairElement.value) return
	return Math.abs(
		pairElement.value.left +
			pairElement.value.width -
			activeElement.value.left -
			activeElement.value.width,
	)
})

const diffTop = computed(() => {
	if (!pairElement.value) return
	return Math.abs(pairElement.value.top - activeElement.value.top)
})

const diffBottom = computed(() => {
	if (!pairElement.value) return
	return Math.abs(
		pairElement.value.top +
			pairedRect.height.value -
			activeElement.value.top -
			activeRect.height.value,
	)
})

const guideStyles = {
	position: 'fixed',
	borderColor: '#70b6f0',
	borderStyle: 'dashed',
}

const leftGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left - 5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const rightGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left + activeElement.value.width + 4.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const topGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top - 5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const bottomGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top + activeRect.height.value + 4.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const updateCenterAlignmentGuides = () => {
	let centerX = slideRect.left.value + slideRect.width.value / 2
	let centerY = slideRect.top.value + slideRect.height.value / 2

	let centerOfElementX = position.value.left + activeRect.width.value / 2
	let centerOfElementY = position.value.top + activeRect.height.value / 2

	showVerticalCenter.value = Math.abs(centerOfElementX - centerX) < 10
	showHorizontalCenter.value = Math.abs(centerOfElementY - centerY) < 10
}

watch(
	() => isDragging.value,
	() => {
		if (!isDragging.value) {
			let centerX = slideRect.left.value + slideRect.width.value / 2
			let centerY = slideRect.top.value + slideRect.height.value / 2

			if (showVerticalCenter.value) {
				position.value = {
					...position.value,
					left: centerX - activeRect.width.value / 2,
				}
			}

			if (showHorizontalCenter.value) {
				position.value = { ...position.value, top: centerY - activeRect.height.value / 2 }
			}

			showVerticalCenter.value = false
			showHorizontalCenter.value = false
		}
	},
)

watch(
	() => position.value,
	() => {
		if (!position.value) return
		let currentScale = slideRect.width.value / 960
		activeElement.value.left = (position.value.left - slideRect.left.value) / currentScale
		activeElement.value.top = (position.value.top - slideRect.top.value) / currentScale

		updateCenterAlignmentGuides()
		snapToPairElement()
	},
	{ immediate: true },
)

watch(
	() => dimensions.value,
	() => {
		if (!dimensions.value) return
		if (activeElement.value && dimensions.value.width != activeElement.value.width) {
			let currentScale = slideRect.width.value / 960
			activeElement.value.width = dimensions.value.width / currentScale
		}
	},
	{ immediate: true },
)

onMounted(() => {
	document.addEventListener('keydown', handleKeyDown)
	document.addEventListener('fullscreenchange', handleScreenChange)
})

onBeforeUnmount(() => {
	document.removeEventListener('keydown', handleKeyDown)
	document.removeEventListener('fullscreenchange', handleScreenChange)
})

defineExpose({
	targetRef,
})

provide('setActiveElement', setActiveElement)
provide('removeDragAndResize', removeDragAndResize)
provide('isDragging', isDragging)
</script>

<style src="../assets/styles/resizer.css"></style>

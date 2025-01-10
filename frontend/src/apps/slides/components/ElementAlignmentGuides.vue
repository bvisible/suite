<template>
	<div
		v-show="Math.abs(diffCenterX) < CENTER_PROXIMITY_THRESHOLD"
		class="absolute left-1/2 h-full w-[1px] -translate-x-1/2 bg-blue-400"
	></div>

	<div
		v-show="Math.abs(diffCenterY) < CENTER_PROXIMITY_THRESHOLD"
		class="absolute top-1/2 h-[1px] w-full -translate-y-1/2 bg-blue-400"
	></div>

	<div v-show="Math.abs(diffLeft) < PROXIMITY_THRESHOLD" :style="leftGuideStyles"></div>
	<div v-show="Math.abs(diffRight) < PROXIMITY_THRESHOLD" :style="rightGuideStyles"></div>
	<div v-show="Math.abs(diffTop) < PROXIMITY_THRESHOLD" :style="topGuideStyles"></div>
	<div v-show="Math.abs(diffBottom) < PROXIMITY_THRESHOLD" :style="bottomGuideStyles"></div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { position, activeSlideElements } from '@/stores/slide'
import { currentDataIndex, currentPairedDataIndex, activeElement } from '@/stores/element'
import { useElementBounding } from '@vueuse/core'

const props = defineProps({
	slideRect: Object,
})

const CENTER_PROXIMITY_THRESHOLD = 20
const PROXIMITY_THRESHOLD = 10

const activeDiv = computed(() => {
	return document.querySelector(`[data-index="${currentDataIndex.value}"]`)
})

const activeRect = useElementBounding(activeDiv)

const pairedDiv = computed(() => {
	return document.querySelector(`[data-index="${currentPairedDataIndex.value}"]`)
})

const pairedRect = useElementBounding(pairedDiv)

const pairElement = computed(() => {
	return activeSlideElements.value[currentPairedDataIndex.value]
})

const snapToCenter = () => {
	if (Math.abs(diffCenterX.value) < CENTER_PROXIMITY_THRESHOLD) {
		const newLeft =
			activeElement.value.left + (diffCenterX.value * 960) / props.slideRect.width.value
		activeElement.value = { ...activeElement.value, left: newLeft }
	}
	if (Math.abs(diffCenterY.value) < CENTER_PROXIMITY_THRESHOLD) {
		const newTop =
			activeElement.value.top + (diffCenterY.value * 960) / props.slideRect.width.value
		activeElement.value = { ...activeElement.value, top: newTop }
	}
}

const snapToPairedElement = () => {
	if (!pairElement.value) return

	const diffs = [
		{ value: diffLeft.value, direction: 'left' },
		{ value: diffRight.value, direction: 'left' },
		{ value: diffTop.value, direction: 'top' },
		{ value: diffBottom.value, direction: 'top' },
	]

	let element = { ...activeElement.value }
	diffs.forEach(({ value, direction }) => {
		if (Math.abs(value) < PROXIMITY_THRESHOLD) {
			element[direction] += value
		}
	})
	activeElement.value = element
}

const diffCenterX = computed(() => {
	if (!position.value) return
	const rect = activeDiv.value.getBoundingClientRect()
	const centerX = props.slideRect.width.value / 2 + props.slideRect.left.value
	const centerOfElementX = rect.left + rect.width / 2
	return centerX - centerOfElementX
})

const diffCenterY = computed(() => {
	if (!position.value) return
	const rect = activeDiv.value.getBoundingClientRect()
	const centerY = props.slideRect.height.value / 2 + props.slideRect.top.value
	const centerOfElementY = rect.top + rect.height / 2
	return centerY - centerOfElementY
})

const diffLeft = computed(() => {
	if (!pairElement.value) return
	return pairElement.value.left - activeElement.value.left
})

const diffRight = computed(() => {
	if (!pairElement.value) return
	return (
		pairElement.value.left +
		pairElement.value.width -
		activeElement.value.left -
		activeElement.value.width
	)
})

const diffTop = computed(() => {
	if (!pairElement.value) return
	return pairElement.value.top - activeElement.value.top
})

const diffBottom = computed(() => {
	if (!pairElement.value) return
	const currentScale = props.slideRect.width.value / 960
	const ogHeight = activeRect.height.value / currentScale
	const ogPairedHeight = pairedRect.height.value / currentScale
	const pairedElementBottom = pairElement.value.top + ogPairedHeight
	const activeElementBottom = activeElement.value.top + ogHeight
	return pairedElementBottom - activeElementBottom
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
		left: `${activeElement.value.left - 6.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const rightGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left + activeElement.value.width + 5.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const topGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top - 6.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const bottomGuideStyles = computed(() => {
	if (!pairElement.value) return
	const currentScale = props.slideRect.width.value / 960
	const originalHeight = activeRect.height.value / currentScale
	return {
		...guideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top + originalHeight + 5.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const setCurrentPairedDataIndex = () => {
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
			elementDiv.top + elementDiv.height - activeRect.top.value - activeRect.height.value,
		)
		if ([diffLeft, diffRight, diffTop, diffBottom].some((diff) => diff < PROXIMITY_THRESHOLD))
			i = index
	})
	currentPairedDataIndex.value = i
}

watch(
	() => position.value,
	() => {
		if (!position.value) return
		setCurrentPairedDataIndex()
		snapToCenter()
		snapToPairedElement()
	},
	{ immediate: true },
)
</script>

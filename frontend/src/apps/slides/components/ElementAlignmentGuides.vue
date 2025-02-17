<template>
	<div v-for="guide in ['centerX', 'centerY']" :key="guide" :style="guideStyles[guide]"></div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useElementBounding } from '@vueuse/core'

import { slide, slideRect } from '@/stores/slide'
import { activePosition, activeElementIds, pairElementId, activeElements } from '@/stores/element'

const props = defineProps({
	scale: Number,
})

// this works kind of like an allowance so after the element is snapped, it can still move away from the center in same mouse event
const RESISTANCE_THRESHOLD = 5

const CENTER_PROXIMITY_THRESHOLD = 20
const PROXIMITY_THRESHOLD = 10

const guideStyles = computed(() => {
	return {
		left: leftGuideStyles.value,
		right: rightGuideStyles.value,
		top: topGuideStyles.value,
		bottom: bottomGuideStyles.value,
		centerX: centerXGuideStyles.value,
		centerY: centerYGuideStyles.value,
	}
})

const activeDiv = computed(() => {
	if (activeElementIds.value.length == 0) return
	else if (activeElementIds.value.length == 1)
		return document.querySelector(`[data-index="${activeElementIds.value[0]}"]`)
	else return document.querySelector('.groupDiv')
})

const activeRect = useElementBounding(activeDiv)

const pairedDiv = computed(() => {
	return document.querySelector(`[data-index="${pairElementId.value}"]`)
})

const pairedRect = useElementBounding(pairedDiv)

const pairElement = computed(() => {
	return slide.value.elements[pairElementId.value]
})

// counters to keep track of how many times the element has been snapped to the center
const snappedX = ref(0)
const snappedY = ref(0)

const snapToCenterX = () => {
	// only allow snapping when -
	// the element is not being dragged away from the center in the same mouse event &&
	// the element is close to the center
	if (
		snappedX.value < RESISTANCE_THRESHOLD &&
		Math.abs(diffCenterX.value) < CENTER_PROXIMITY_THRESHOLD
	) {
		activePosition.value = {
			...activePosition.value,
			left: activePosition.value.left + diffCenterX.value * props.scale,
		}
		snappedX.value += 1
	}
	// else reset the counter for snapping
	else {
		snappedX.value = 0
	}
}

const snapToCenterY = () => {
	if (
		snappedY.value < RESISTANCE_THRESHOLD &&
		Math.abs(diffCenterY.value) < CENTER_PROXIMITY_THRESHOLD
	) {
		activePosition.value = {
			...activePosition.value,
			top: activePosition.value.top + diffCenterY.value * props.scale,
		}
		snappedY.value += 1
	} else {
		snappedY.value = 0
	}
}

const snapToPairedElement = () => {
	if (!pairElement.value) return
	let element = { ...activeElement.value }
	const l = Math.abs(diffLeft.value) < PROXIMITY_THRESHOLD ? diffLeft.value : 0
	const r = Math.abs(diffRight.value) < PROXIMITY_THRESHOLD ? diffRight.value : 0
	if (Math.abs(l) > Math.abs(r)) {
		element.left += l
	} else {
		element.left += r
	}

	const t = Math.abs(diffTop.value) < PROXIMITY_THRESHOLD ? diffTop.value : 0
	const b = Math.abs(diffBottom.value) < PROXIMITY_THRESHOLD ? diffBottom.value : 0
	if (Math.abs(t) > Math.abs(b)) {
		element.top += t
	} else {
		element.top += b
	}
	activeElement.value = element
}

const diffCenterX = computed(() => {
	if (!activePosition.value) return
	const centerX = slideRect.value.width / 2 + slideRect.value.left
	const centerOfElementX = activeRect.left.value + activeRect.width.value / 2
	return centerX - centerOfElementX
})

const diffCenterY = computed(() => {
	if (!activePosition.value) return
	const centerY = slideRect.value.height / 2 + slideRect.value.top
	const centerOfElementY = activeRect.top.value + activeRect.height.value / 2
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
	const ogHeight = activeRect.height.value / props.scale
	const ogPairedHeight = pairedRect.height.value / props.scale
	const pairedElementBottom = pairElement.value.top + ogPairedHeight
	const activeElementBottom = activeElement.value.top + ogHeight
	return pairedElementBottom - activeElementBottom
})

const commonGuideStyles = {
	position: 'fixed',
	borderColor: '#70b6f080',
	borderStyle: 'dashed',
}

const leftGuideStyles = computed(() => {
	if (diffLeft.value == undefined || Math.abs(diffLeft.value) > PROXIMITY_THRESHOLD) return ''
	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left - 6.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const rightGuideStyles = computed(() => {
	if (diffRight.value == undefined || Math.abs(diffRight.value) > PROXIMITY_THRESHOLD) return ''
	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left + activeElement.value.width + 5.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const topGuideStyles = computed(() => {
	if (diffTop.value == undefined || Math.abs(diffTop.value) > PROXIMITY_THRESHOLD) return ''
	return {
		...commonGuideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top - 6.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const bottomGuideStyles = computed(() => {
	if (diffBottom.value == undefined || Math.abs(diffBottom.value) > PROXIMITY_THRESHOLD) return ''
	const originalHeight = activeRect.height.value / props.scale
	return {
		...commonGuideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top + originalHeight + 5.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const centerXGuideStyles = computed(() => {
	if (Math.abs(diffCenterX.value) > CENTER_PROXIMITY_THRESHOLD) return ''
	return {
		backgroundColor: '#70b6f080',
		height: '100%',
		width: '1px',
		position: 'fixed',
		left: '50%',
	}
})

const centerYGuideStyles = computed(() => {
	if (Math.abs(diffCenterY.value) > CENTER_PROXIMITY_THRESHOLD) return ''
	return {
		backgroundColor: '#70b6f080',
		width: '100%',
		height: '1px',
		position: 'fixed',
		top: '50%',
	}
})

const setCurrentPairedDataIndex = () => {
	if (!activeElement.value) return
	let i = null
	slide.value.elements.forEach((element, index) => {
		if (index == activeElementId.value) return
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
	pairElementId.value = i
}

watch(
	() => diffCenterX.value,
	() => {
		snapToCenterX()
	},
	{ immediate: true },
)

watch(
	() => diffCenterY.value,
	() => {
		snapToCenterY()
	},
	{ immediate: true },
)
</script>

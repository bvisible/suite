<template>
	<div
		v-for="guide in ['centerX', 'centerY', 'left', 'right']"
		:key="guide"
		:style="guideStyles[guide]"
	></div>
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
const RESISTANCE_THRESHOLD = 10

const CENTER_PROXIMITY_THRESHOLD = 20
const PROXIMITY_THRESHOLD = 7

const guideStyles = computed(() => {
	return {
		left: leftGuideStyles.value,
		right: rightGuideStyles.value,
		centerX: centerXGuideStyles.value,
		centerY: centerYGuideStyles.value,
	}
})

const activeDiv = computed(() => {
	if (activeElementIds.value.length == 0) return
	return document.querySelector('.groupDiv')
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
const snapCountX = ref(0)
const snapCountY = ref(0)
const snapCountLeft = ref(0)
const snapCountRight = ref(0)

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

const getDiffFromCenter = (axis) => {
	if (!activePosition.value) return
	let slideCenter, elementCenter
	if (axis == 'X') {
		slideCenter = slideRect.value.width / 2 + slideRect.value.left
		elementCenter = activeRect.left.value + activeRect.width.value / 2
	} else {
		slideCenter = slideRect.value.height / 2 + slideRect.value.top
		elementCenter = activeRect.top.value + activeRect.height.value / 2
	}
	return slideCenter - elementCenter
}

const diffCenterX = computed(() => getDiffFromCenter('X'))

const diffCenterY = computed(() => getDiffFromCenter('Y'))

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
	if (!pairElement.value || Math.abs(diffWithPaired.value.left) > PROXIMITY_THRESHOLD) return ''
	const pairedTop = pairElement.value.top
	const pairedHeight = pairedRect.height.value
	const diffHeight = pairedTop < activePosition.value.top ? activeRect.height.value : pairedHeight
	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activePosition.value.left - 2}px`,
		top: `${Math.min(activePosition.value.top, pairedTop)}px`,
		height: `${Math.abs(pairedTop - activePosition.value.top) + diffHeight}px`,
	}
})

const rightGuideStyles = computed(() => {
	if (!pairElement.value || Math.abs(diffWithPaired.value.right) > PROXIMITY_THRESHOLD) return ''
	const pairedTop = pairElement.value.top
	const pairedHeight = pairedRect.height.value
	const diffHeight = pairedTop < activePosition.value.top ? activeRect.height.value : pairedHeight
	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activePosition.value.left + activeRect.width.value - 4}px`,
		top: `${Math.min(activePosition.value.top, pairedTop)}px`,
		height: `${Math.abs(pairedTop - activePosition.value.top) + diffHeight}px`,
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

// decides the paired element based on proximity and sets the diffWithPaired
const handleElementPairing = () => {
	const selectionLeft = activePosition.value.left
	const selectionRight = activePosition.value.left + activeRect.width.value
	let i
	slide.value.elements.forEach((element, index) => {
		if (activeElementIds.value.includes(index)) return
		const elementLeft = element.left
		const elementRight = element.left + element.width
		const diffLeft = Math.abs(selectionLeft - elementLeft)
		const diffRight = Math.abs(selectionRight - elementRight)
		if (diffLeft < PROXIMITY_THRESHOLD || diffRight < PROXIMITY_THRESHOLD) i = index
	})
	pairElementId.value = i
	setDiffWithPaired()
}

const diffWithPaired = ref({ left: 0, right: 0, top: 0, bottom: 0 })

const setDiffWithPaired = () => {
	if (!pairElement.value) return
	const { left, top, width, height } = pairElement.value
	diffWithPaired.value = {
		left: left - activePosition.value.left + 2,
		right: left + width - activePosition.value.left - activeRect.width.value + 2,
	}
}

const updateDiffsBasedOnSnap = (movement, diff, threshold, snapCount) => {
	const canSnap = Math.abs(diff) < threshold
	const withinResistanceThreshold = snapCount.value < RESISTANCE_THRESHOLD

	// only allow snapping when -
	// the element is within the range of the snapping threshold
	// the element is not being forced to snap while being dragged away
	if (canSnap && withinResistanceThreshold) {
		movement += diff
		snapCount.value += 1
	} else {
		snapCount.value = 0
	}

	// if element crosses the resistance threshold, it should not be allowed to move again
	if (!withinResistanceThreshold) {
		movement = threshold * Math.sign(movement)
		snapCount.value = 0
	}

	return movement
}

const updateElementPosition = (dx, dy) => {
	if (!activePosition.value) return

	dx = updateDiffsBasedOnSnap(dx, diffCenterX.value, CENTER_PROXIMITY_THRESHOLD, snapCountX)
	dy = updateDiffsBasedOnSnap(dy, diffCenterY.value, CENTER_PROXIMITY_THRESHOLD, snapCountY)

	handleElementPairing()
	if (pairElement.value) {
		if (Math.abs(diffWithPaired.value.left) < Math.abs(diffWithPaired.value.right)) {
			dx = updateDiffsBasedOnSnap(
				dx,
				diffWithPaired.value.left,
				PROXIMITY_THRESHOLD,
				snapCountLeft,
			)
		} else {
			dx = updateDiffsBasedOnSnap(
				dx,
				diffWithPaired.value.right,
				PROXIMITY_THRESHOLD,
				snapCountRight,
			)
		}
	}

	activePosition.value = {
		left: activePosition.value.left + dx,
		top: activePosition.value.top + dy,
	}
}

const handleArrowKeys = (key) => {
	let dx = 0
	let dy = 0

	if (key == 'ArrowLeft') dx = -1
	else if (key == 'ArrowRight') dx = 1
	else if (key == 'ArrowUp') dy = -1
	else if (key == 'ArrowDown') dy = 1

	updateElementPosition(dx, dy)
}

defineExpose({
	handleArrowKeys,
	updateElementPosition,
})
</script>

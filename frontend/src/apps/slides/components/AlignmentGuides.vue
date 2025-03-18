<template>
	<div
		v-for="guide in ['centerX', 'centerY', 'left', 'right', 'top', 'bottom']"
		:key="guide"
		:style="guideStyles[guide]"
	></div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useElementBounding } from '@vueuse/core'

import { slide, slideDimensions } from '@/stores/slide'
import { activePosition, activeElementIds, pairElementId } from '@/stores/element'

const PROXIMITY_THRESHOLD = 15

const activeDiv = computed(() => {
	if (activeElementIds.value.length == 0) return
	return document.querySelector('.groupDiv')
})

const pairedDiv = computed(() => {
	return document.querySelector(`[data-index="${pairElementId.value}"]`)
})

const pairedRect = useElementBounding(pairedDiv)

const pairElement = computed(() => {
	return slide.value.elements[pairElementId.value]
})

const prevDiffs = ref({
	centerX: 0,
	centerY: 0,
	left: 0,
	right: 0,
	top: 0,
	bottom: 0,
})

const diffs = ref({
	centerX: null,
	centerY: null,
	left: null,
	right: null,
	top: null,
	bottom: null,
})

const visibilityMap = computed(() => {
	if (!activePosition.value || diffs.value.centerX == null)
		return {
			centerX: false,
			centerY: false,
			left: false,
			right: false,
			top: false,
			bottom: false,
		}
	return {
		centerX: Math.abs(diffs.value.centerX) < PROXIMITY_THRESHOLD,
		centerY: Math.abs(diffs.value.centerY) < PROXIMITY_THRESHOLD,
		left: Math.abs(diffs.value.left) < PROXIMITY_THRESHOLD,
		right: Math.abs(diffs.value.right) < PROXIMITY_THRESHOLD,
		top: Math.abs(diffs.value.top) < PROXIMITY_THRESHOLD,
		bottom: Math.abs(diffs.value.bottom) < PROXIMITY_THRESHOLD,
	}
})

// when an element is snapped to a new position, enable movement after a few frames
const skipFrames = ref(0)

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

const commonGuideStyles = {
	position: 'fixed',
	borderColor: '#70b6f080',
	borderStyle: 'dashed',
}

const getVerticalGuideStyles = (direction) => {
	if (!pairElement.value || !activePosition.value || !visibilityMap.value[direction]) return ''

	const activeBounds = getElementBounds(activeDiv.value)
	const pairedBounds = getElementBounds(pairedDiv.value)

	const left = direction == 'left' ? activeBounds.left - 1 : activeBounds.right
	const top = Math.min(activeBounds.top, pairedBounds.top)

	const lastElementHeight =
		pairedBounds.top < activeBounds.top ? activeBounds.height : pairedBounds.height
	const height = Math.abs(pairedBounds.top - activeBounds.top) + lastElementHeight

	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${left}px`,
		top: `${top}px`,
		height: `${height}px`,
	}
}

const leftGuideStyles = computed(() => getVerticalGuideStyles('left'))

const rightGuideStyles = computed(() => getVerticalGuideStyles('right'))

const getHorizontalGuideStyles = (direction, diffWithPaired) => {
	if (!pairElement.value || !activePosition.value || !visibilityMap.value[direction]) return ''

	const activeBounds = getElementBounds(activeDiv.value)
	const pairedBounds = getElementBounds(pairedDiv.value)

	const top = direction == 'top' ? activeBounds.top - 1 : activeBounds.bottom
	const left = Math.min(activeBounds.left, pairedBounds.left)

	const lastElementWidth =
		pairedBounds.left < activeBounds.left ? activeBounds.width : pairedBounds.width
	const width = Math.abs(pairedBounds.left - activeBounds.left) + lastElementWidth

	return {
		...commonGuideStyles,
		borderWidth: '1px 0 0 0',
		top: `${top}px`,
		left: `${left}px`,
		width: `${width}px`,
	}
}

const topGuideStyles = computed(() => getHorizontalGuideStyles('top'))

const bottomGuideStyles = computed(() => getHorizontalGuideStyles('bottom'))

const centerXGuideStyles = computed(() => {
	if (!visibilityMap.value.centerX) return ''
	return {
		backgroundColor: '#70b6f080',
		height: '100%',
		width: '1px',
		position: 'fixed',
		left: '50%',
	}
})

const centerYGuideStyles = computed(() => {
	if (!visibilityMap.value.centerY) return ''
	return {
		backgroundColor: '#70b6f080',
		width: '100%',
		height: '1px',
		position: 'fixed',
		top: '50%',
	}
})

const getScaledValue = (value, axis) => {
	if (axis == 'X') return (value - slideDimensions.left) / slideDimensions.scale
	return (value - slideDimensions.top) / slideDimensions.scale
}

const getElementBounds = (div) => {
	const rect = div.getBoundingClientRect()
	return {
		left: getScaledValue(rect.left, 'X'),
		top: getScaledValue(rect.top, 'Y'),
		right: getScaledValue(rect.right, 'X'),
		bottom: getScaledValue(rect.bottom, 'Y'),
		height: rect.height / slideDimensions.scale,
		width: rect.width / slideDimensions.scale,
	}
}

const getMovementAfterSnap = (diff, prevDiff) => {
	let change = 0
	const canSnap =
		Math.abs(diff + PROXIMITY_THRESHOLD) < 3 || Math.abs(diff - PROXIMITY_THRESHOLD) < 3

	const movingAway = Math.abs(diff) > Math.abs(prevDiff)

	if (canSnap && !movingAway) {
		change -= diff
	}
	return change
}

const getPairedOffsets = (dx, dy) => {
	let offsetLeft = 0,
		offsetTop = 0

	const diffLeft = diffs.value.left
	const diffRight = diffs.value.right
	const diffTop = diffs.value.top
	const diffBottom = diffs.value.bottom

	if (Math.abs(diffRight) < Math.abs(diffLeft)) {
		offsetLeft = getMovementAfterSnap(diffRight, prevDiffs.value.right)
	} else {
		offsetLeft = getMovementAfterSnap(diffLeft, prevDiffs.value.left)
	}

	if (Math.abs(diffBottom) < Math.abs(diffTop)) {
		offsetTop = getMovementAfterSnap(diffBottom, prevDiffs.value.bottom)
	} else {
		offsetTop = getMovementAfterSnap(diffTop, prevDiffs.value.top)
	}

	return { offsetLeft, offsetTop }
}

const getDiffFromCenter = (axis) => {
	if (!activePosition.value) return
	let slideCenter, elementCenter

	const activeBounds = getElementBounds(activeDiv.value)

	if (axis == 'X') {
		slideCenter = slideDimensions.width / slideDimensions.scale / 2
		elementCenter = activeBounds.left + activeBounds.width / 2
	} else {
		slideCenter = slideDimensions.height / slideDimensions.scale / 2
		elementCenter = activeBounds.top + activeBounds.height / 2
	}

	return elementCenter - slideCenter
}

const getCenterOffsets = (dx, dy) => {
	let offsetX = 0,
		offsetY = 0

	offsetX = getMovementAfterSnap(diffs.value.centerX, prevDiffs.value.centerX)
	offsetY = getMovementAfterSnap(diffs.value.centerY, prevDiffs.value.centerY)

	return { offsetX, offsetY }
}

const canElementPair = (diffLeft, diffRight, diffTop, diffBottom) => {
	return (
		Math.abs(diffLeft) < PROXIMITY_THRESHOLD ||
		Math.abs(diffRight) < PROXIMITY_THRESHOLD ||
		Math.abs(diffTop) < PROXIMITY_THRESHOLD ||
		Math.abs(diffBottom) < PROXIMITY_THRESHOLD
	)
}

const setCurrentDiffs = () => {
	slide.value.elements.forEach((element, index) => {
		if (activeElementIds.value.includes(index)) return

		const elementDiv = document.querySelector(`[data-index="${index}"]`)
		if (!elementDiv || !activeDiv.value) return

		const activeBounds = getElementBounds(activeDiv.value)
		const elementBounds = getElementBounds(elementDiv)

		const diffLeft = activeBounds.left - elementBounds.left
		const diffRight = activeBounds.right - elementBounds.right
		const diffTop = activeBounds.top - elementBounds.top
		const diffBottom = activeBounds.bottom - elementBounds.bottom

		const canPair = canElementPair(diffLeft, diffRight, diffTop, diffBottom)
		const isPaired = pairElementId.value == index

		if (canPair) {
			pairElementId.value = index
		} else if (isPaired) {
			pairElementId.value = null
		}

		diffs.value.left = diffLeft
		diffs.value.right = diffRight
		diffs.value.top = diffTop
		diffs.value.bottom = diffBottom
	})

	diffs.value.centerX = getDiffFromCenter('X')
	diffs.value.centerY = getDiffFromCenter('Y')
}

const updatePrevDiffs = () => {
	prevDiffs.value = JSON.parse(JSON.stringify(diffs.value))
}

const updateMovementBasedOnSnap = (dx, dy) => {
	setCurrentDiffs()

	const { offsetX, offsetY } = getCenterOffsets(dx, dy)

	const { offsetLeft, offsetTop } = getPairedOffsets(dx, dy)

	updatePrevDiffs()

	const updatedDx = dx + offsetX + offsetLeft
	const updatedDy = dy + offsetY + offsetTop

	return { updatedDx, updatedDy }
}

const updateElementPosition = (dx, dy) => {
	if (!activePosition.value) return

	const { updatedDx, updatedDy } = updateMovementBasedOnSnap(dx, dy)

	const didSnap = dx != updatedDx || dy != updatedDy

	if (!skipFrames.value)
		activePosition.value = {
			left: activePosition.value.left + updatedDx,
			top: activePosition.value.top + updatedDy,
		}
	else skipFrames.value -= 1

	if (didSnap) {
		skipFrames.value = 15
	}
}

defineExpose({
	updateElementPosition,
})
</script>

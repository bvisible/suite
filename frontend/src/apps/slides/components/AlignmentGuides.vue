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

import { slide, slideRect } from '@/stores/slide'
import { activePosition, activeElementIds, pairElementId } from '@/stores/element'

const props = defineProps({
	scale: Number,
})

// this works kind of like an allowance so after the element is snapped, it can still move away from the center in same mouse event
const RESISTANCE_THRESHOLD = 10

const CENTER_PROXIMITY_THRESHOLD = 14
const PROXIMITY_THRESHOLD = 10

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
const prevDiffs = ref({
	centerX: 0,
	centerY: 0,
	left: 0,
	right: 0,
	top: 0,
	bottom: 0,
})

const skip = ref(0)

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

const getVerticalGuideStyles = (direction, diffWithPaired) => {
	if (!pairElement.value || Math.abs(diffWithPaired) > PROXIMITY_THRESHOLD) return ''

	let left = (activeRect.left.value - slideRect.value.left) / props.scale

	const top = (activeRect.top.value - slideRect.value.top) / props.scale
	const pairedTop = (pairedRect.top.value - slideRect.value.top) / props.scale

	const diffHeight =
		pairedTop < top
			? activeRect.height.value / props.scale
			: pairedRect.height.value / props.scale

	if (direction == 'right') left += activeRect.width.value / props.scale + 1

	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${left - 1}px`,
		top: `${Math.min(top, pairedTop)}px`,
		height: `${Math.abs(pairedTop - top) + diffHeight}px`,
	}
}

const leftGuideStyles = computed(() => getVerticalGuideStyles('left', diffWithPaired.value.left))

const rightGuideStyles = computed(() => getVerticalGuideStyles('right', diffWithPaired.value.right))

const getHorizontalGuideStyles = (direction, diffWithPaired) => {
	if (!pairElement.value || Math.abs(diffWithPaired) > PROXIMITY_THRESHOLD) return ''

	let top = (activeRect.top.value - slideRect.value.top) / props.scale

	const left = (activeRect.left.value - slideRect.value.left) / props.scale
	const pairedLeft = (pairedRect.left.value - slideRect.value.left) / props.scale

	const diffWidth =
		pairedLeft < left
			? activeRect.width.value / props.scale
			: pairedRect.width.value / props.scale

	if (direction == 'bottom') top += activeRect.height.value / props.scale + 1

	return {
		...commonGuideStyles,
		borderWidth: '1px 0 0 0',
		top: `${top - 1}px`,
		left: `${Math.min(left, pairedLeft)}px`,
		width: `${Math.abs(pairedLeft - left) + diffWidth}px`,
	}
}

const topGuideStyles = computed(() => getHorizontalGuideStyles('top', diffWithPaired.value.top))

const bottomGuideStyles = computed(() =>
	getHorizontalGuideStyles('bottom', diffWithPaired.value.bottom),
)

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

const isElementWithinProximity = (element, index) => {
	const left = activeRect.left.value
	const top = activeRect.top.value
	const right = left + activeRect.width.value
	const bottom = top + activeRect.height.value

	const elementDiv = document.querySelector(`[data-index="${index}"]`)
	if (!elementDiv) return

	const elementRect = elementDiv.getBoundingClientRect()

	const diffLeft = Math.abs(left - elementRect.left)
	const diffRight = Math.abs(right - elementRect.right)
	const diffTop = Math.abs(top - elementRect.top)
	const diffBottom = Math.abs(bottom - elementRect.bottom)

	return [diffLeft, diffRight, diffTop, diffBottom].some((diff) => diff < PROXIMITY_THRESHOLD)
}

// decides the paired element based on proximity and sets the diffWithPaired
const handleElementPairing = () => {
	let i
	slide.value.elements.forEach((element, index) => {
		if (activeElementIds.value.includes(index)) return
		const withinProximity = isElementWithinProximity(element, index)
		if (withinProximity) i = index
	})

	pairElementId.value = i
	setDiffWithPaired()
}

const diffWithPaired = ref({ left: 0, right: 0, top: 0, bottom: 0 })

const setDiffWithPaired = () => {
	if (!pairElement.value) return
	diffWithPaired.value = {
		left: activeRect.left.value - pairedRect.left.value,
		right: activeRect.right.value - pairedRect.right.value,
		top: activeRect.top.value - pairedRect.top.value,
		bottom: activeRect.bottom.value - pairedRect.bottom.value,
	}
}

const updateMovement = (movement, nextPosition, prevPosition, matchPosition, threshold) => {
	const canSnap =
		Math.abs(nextPosition - matchPosition + threshold) < 3 ||
		Math.abs(nextPosition - matchPosition - threshold) < 3

	const newdiff = Math.abs(matchPosition - nextPosition)

	const movingAway = newdiff > prevPosition

	// only allow snapping when -
	// the element is within the range of the snapping threshold
	// the element is not being forced to snap while being dragged away
	if (canSnap && !movingAway) {
		movement += matchPosition - nextPosition
	}

	return movement
}

const pickClosestSnapDirection = (axis, a, b) => {
	let diff, count
	if (Math.abs(a) < Math.abs(b)) {
		diff = a
		count = axis == 'X' ? snapCountLeft : snapCountTop
	} else {
		diff = b
		count = axis == 'X' ? snapCountRight : snapCountBottom
	}
	return { diff, count }
}

const updateMovementBasedOnSnap = (dx, dy) => {
	let updatedDx = dx,
		updatedDy = dy

	// check for snapping to the center and update movement
	const slideCenterX = slideRect.value.width / 2 + slideRect.value.left
	const slideCenterY = slideRect.value.height / 2 + slideRect.value.top

	const newCenterX = activeRect.left.value + activeRect.width.value / 2 + dx
	const newCenterY = activeRect.top.value + activeRect.height.value / 2 + dy

	updatedDx = updateMovement(
		dx,
		newCenterX,
		prevDiffs.value.centerX,
		slideCenterX,
		CENTER_PROXIMITY_THRESHOLD,
	)
	updatedDy = updateMovement(
		dy,
		newCenterY,
		prevDiffs.value.centerY,
		slideCenterY,
		CENTER_PROXIMITY_THRESHOLD,
	)

	// check for any possible element pairing and update movement
	handleElementPairing()
	if (!pairElement.value) return { updatedDx, updatedDy }

	// check for which direction to snap in - snap to closest direction instead of pulling towards both

	let prevX, newX, pairedX
	if (Math.abs(diffWithPaired.value.right) < Math.abs(diffWithPaired.value.left)) {
		prevX = prevDiffs.value.right
		newX = activeRect.right.value + dx
		pairedX = pairedRect.right.value
	} else {
		prevX = prevDiffs.value.left
		newX = activeRect.left.value + dx
		pairedX = pairedRect.left.value
	}

	updatedDx = updateMovement(dx, newX, prevX, pairedX, PROXIMITY_THRESHOLD)

	let prevY, newY, pairedY
	if (Math.abs(diffWithPaired.value.bottom) < Math.abs(diffWithPaired.value.top)) {
		prevY = prevDiffs.value.bottom
		newY = activeRect.bottom.value + dy
		pairedY = pairedRect.bottom.value
	} else {
		prevY = prevDiffs.value.top
		newY = activeRect.top.value + dy
		pairedY = pairedRect.top.value
	}

	updatedDy = updateMovement(dy, newY, prevY, pairedY, PROXIMITY_THRESHOLD)

	return { updatedDx, updatedDy }
}

const updateElementPosition = (dx, dy) => {
	if (!activePosition.value) return

	const { updatedDx, updatedDy } = updateMovementBasedOnSnap(dx, dy)

	const didSnap = dx != updatedDx || dy != updatedDy

	if (!skip.value)
		activePosition.value = {
			left: activePosition.value.left + updatedDx,
			top: activePosition.value.top + updatedDy,
		}
	else skip.value -= 1

	prevDiffs.value = {
		centerX: Math.abs(diffCenterX.value),
		centerY: Math.abs(diffCenterY.value),
		left: Math.abs(diffWithPaired.value.left),
		right: Math.abs(diffWithPaired.value.right),
		top: Math.abs(diffWithPaired.value.top),
		bottom: Math.abs(diffWithPaired.value.bottom),
	}

	if (didSnap) {
		skip.value = 20
	}
}

defineExpose({
	updateElementPosition,
})
</script>

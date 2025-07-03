import { ref, reactive, computed } from 'vue'
import { selectionBounds, slide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'

export const useSnapping = (target, parent) => {
	const directionKeys = ['left', 'centerX', 'right', 'top', 'centerY', 'bottom']

	const snapMovement = ref({ x: 0, y: 0 })

	const initDiffs = () => {
		return directionKeys.reduce((map, direction) => {
			map[direction] = null
			return map
		}, {})
	}

	const diffs = reactive(initDiffs())
	const prevDiffs = reactive(initDiffs())
	const resistanceMap = reactive(initDiffs())

	const visibilityMap = computed(() => {
		if (!target.value) return

		return directionKeys.reduce((visibility, direction) => {
			const diff = Math.abs(diffs[direction])
			const threshold = getDynamicThresholds(direction).threshold

			visibility[direction] = Math.abs(diff) < threshold
			return visibility
		}, {})
	})

	const getSlideCenter = (axis) => {
		let slideStart, slideSize

		if (axis == 'Y') {
			slideStart = slideBounds.left
			slideSize = slideBounds.width
		} else {
			slideStart = slideBounds.top
			slideSize = slideBounds.height
		}

		return slideStart + slideSize / 2
	}

	const getElementCenter = (axis) => {
		if (!target.value) return
		let elementStart, elementSize, slideStart

		if (axis == 'Y') {
			elementStart = selectionBounds.left
			elementSize = selectionBounds.width
			slideStart = slideBounds.left
		} else {
			elementStart = selectionBounds.top
			elementSize = selectionBounds.height
			slideStart = slideBounds.top
		}

		elementStart = elementStart * slideBounds.scale + slideStart
		elementSize *= slideBounds.scale

		return elementStart + elementSize / 2
	}

	const getDiffFromCenter = (axis) => {
		if (!target.value) return

		const slideCenter = getSlideCenter(axis)
		const elementCenter = getElementCenter(axis)

		return slideCenter - elementCenter
	}

	const setCenterDiffs = () => {
		if (!target.value) return

		diffs.centerX = getDiffFromCenter('X')
		diffs.centerY = getDiffFromCenter('Y')
	}

	const canElementPair = (diffsFromElement) => {
		if (!diffsFromElement) return false

		return Object.values(diffsFromElement).some((direction, diff) => {
			const threshold = getDynamicThresholds(direction).threshold
			return Math.abs(diff) < threshold
		})
	}

	const getActiveElementBounds = () => {
		const scale = slideBounds.scale

		const bounds = Object.fromEntries(
			Object.entries(selectionBounds).map(([key, value]) => [key, value * scale]),
		)

		return {
			left: bounds.left + slideBounds.left,
			right: bounds.left + bounds.width + slideBounds.left,
			top: bounds.top + slideBounds.top,
			bottom: bounds.top + bounds.height + slideBounds.top,
		}
	}

	const getDiffFromElement = (element) => {
		if (activeElementIds.value.includes(element.id)) return

		const elementDiv = document.querySelector(`[data-index="${element.id}"]`)
		if (!elementDiv || !target.value) return

		const elementBounds = elementDiv.getBoundingClientRect()
		const activeBounds = getActiveElementBounds()

		return {
			left: activeBounds.left - elementBounds.left,
			right: activeBounds.right - elementBounds.right,
			top: activeBounds.top - elementBounds.top,
			bottom: activeBounds.bottom - elementBounds.bottom,
		}
	}

	const pairElement = (id, diffFromElement) => {
		if (!diffFromElement) return

		pairElementId.value = id

		Object.assign(diffs, diffFromElement)
	}

	const unpairElement = () => {
		pairElementId.value = null

		const resetDiffs = () => {
			return ['left', 'right', 'top', 'bottom'].reduce((map, direction) => {
				map[direction] = null
				return map
			}, {})
		}

		Object.assign(diffs, resetDiffs())
		Object.assign(resistanceMap, resetDiffs())
		Object.assign(prevDiffs, resetDiffs())
	}

	const setPairedDiffs = () => {
		slide.value.elements.forEach((element) => {
			const diffFromElement = getDiffFromElement(element)

			const canPair = canElementPair(diffFromElement)
			const isPaired = pairElementId.value == element.id

			if (canPair) pairElement(element.id, diffFromElement)
			else if (isPaired) unpairElement()
		})
	}

	const updateDiffs = () => {
		if (!target.value) return

		Object.assign(prevDiffs, diffs)

		setCenterDiffs()

		setPairedDiffs()
	}

	const getDynamicThresholds = (axis) => {
		const scaleFactor = 0.1
		const scaledWidth = selectionBounds.width * slideBounds.scale * scaleFactor
		const minThreshold = ['centerX', 'centerY'].includes(axis) ? scaledWidth / 2 : 10
		const maxThreshold = ['centerX', 'centerY'].includes(axis) ? scaledWidth * 2 : 100

		return {
			threshold: Math.max(minThreshold, Math.min(maxThreshold, scaledWidth)),
			resistance_threshold: scaledWidth * 0.15,
		}
	}

	const getDiffsForAxis = (axis) => {
		return {
			diff: diffs[axis],
			prevDiff: prevDiffs[axis],
		}
	}

	const getThresholdsAndMargin = (axis) => {
		return {
			...getDynamicThresholds(axis),
			margin: ['centerX', 'centerY'].includes(axis) ? 1 : 5,
		}
	}

	const handleSnapMovement = (axis) => {
		const isMovingAway = () => {
			if (diff == null || prevDiff == null) return false

			// If current diff is greater, element is moving away
			const currDiffGreater = Math.abs(diff) >= Math.abs(prevDiff)

			// If element just snapped, the prev diff is the threshold point
			const justSnapped = Math.abs(Math.abs(prevDiff) - threshold) < margin

			return currDiffGreater || justSnapped
		}

		const getSnapOffset = () => {
			// check for threshold + / - margin
			const canSnap = Math.abs(Math.abs(diff) - threshold) < margin
			if (canSnap && !movingAway) return diff
			return 0
		}

		const setResistanceMap = () => {
			const withinResistanceRange = movingAway && Math.abs(diff) < resistance_threshold

			resistanceMap[axis] = diff !== null && withinResistanceRange
		}

		const { diff, prevDiff } = getDiffsForAxis(axis)

		const { threshold, resistance_threshold, margin } = getThresholdsAndMargin(axis)

		const movingAway = isMovingAway()

		setResistanceMap()

		return getSnapOffset()
	}

	const getCenterOffsets = () => {
		return {
			offsetX: handleSnapMovement('centerY'),
			offsetY: handleSnapMovement('centerX'),
		}
	}

	const getOffset = (axis) => {
		let start, end

		if (axis == 'X') {
			start = 'left'
			end = 'right'
		} else {
			start = 'top'
			end = 'bottom'
		}

		if (Math.abs(diffs[end]) < Math.abs(diffs[start])) return handleSnapMovement(end)

		return handleSnapMovement(start)
	}

	const getPairedOffsets = () => {
		return {
			offsetLeft: getOffset('X'),
			offsetTop: getOffset('Y'),
		}
	}

	const getSnapDelta = () => {
		if (!target.value) return

		const { offsetX, offsetY } = getCenterOffsets()

		const { offsetLeft, offsetTop } = getPairedOffsets()

		return {
			x: offsetX - offsetLeft,
			y: offsetY - offsetTop,
		}
	}

	const handleSnapping = () => {
		// update diffs based on current position
		updateDiffs()

		// return delta to apply for closest snap
		return getSnapDelta()
	}

	return {
		visibilityMap,
		resistanceMap,
		handleSnapping,
	}
}

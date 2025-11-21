import { ref, reactive, computed } from 'vue'
import { selectionBounds, currentSlide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'

export const useSnapping = (target, parent, currentResizer, hasOngoingInteraction) => {
	// element wrt slide center
	const slideCenterAlignmentKeys = ['centerX', 'centerY', 'startX', 'startY', 'endX', 'endY']

	// element wrt other elements
	const matchedStartAlignmentKeys = ['startX', 'startY', 'endX', 'endY']
	const matchedEndAlignmentKeys = ['startX', 'startY', 'endX', 'endY']

	const initDiffs = () => {
		const makeNullMap = (keys) => {
			const map = {}
			keys.forEach((k) => (map[k] = null))
			return map
		}

		return {
			slideCenter: makeNullMap(slideCenterAlignmentKeys),
			matchedStart: makeNullMap(matchedStartAlignmentKeys),
			matchedEnd: makeNullMap(matchedStartAlignmentKeys),
		}
	}

	const diffs = reactive(initDiffs())
	const prevDiffs = reactive(initDiffs())
	const resistanceMap = reactive({
		centerX: false,
		centerY: false,
		left: false,
		right: false,
		top: false,
		bottom: false,
	})

	const visibilityMap = reactive({
		centerX: true,
		centerY: true,
		left: true,
		right: true,
		top: true,
		bottom: true,
	})

	const mode = ref(null)

	const getGuideForDirection = (direction) => {
		switch (direction) {
			case 'slideCenterY':
			case 'startY':
			case 'endY':
				return 'centerX'
			case 'slideCenterX':
			case 'startX':
			case 'endX':
				return 'centerY'
			default:
				return direction
		}
	}

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

	const updateDiffsRelativeToSlide = () => {
		if (!target.value) return

		diffs.slideCenter.centerX = getDiffFromCenter('Y')
		diffs.slideCenter.centerY = getDiffFromCenter('X')

		if (mode.value == 'dragging') return

		diffs.slideCenter.startX =
			getDiffFromCenter('Y') + (selectionBounds.width * slideBounds.scale) / 2
		diffs.slideCenter.endX =
			getDiffFromCenter('Y') - (selectionBounds.width * slideBounds.scale) / 2
	}

	const canElementPair = (diffsFromElement) => {
		if (!diffsFromElement) return false

		return Object.entries(diffsFromElement).some(([direction, diff]) => {
			const threshold = getDynamicThresholds(direction).threshold
			return diff !== null && Math.abs(diff) < threshold
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

		diffs.matchedStart.startX = diffFromElement.left
		diffs.matchedEnd.endX = diffFromElement.right

		diffs.matchedStart.startY = diffFromElement.top
		diffs.matchedEnd.endY = diffFromElement.bottom
	}

	const unpairElement = () => {
		pairElementId.value = null

		const resetDiffs = () => {
			return ['startX', 'startY', 'endX', 'endY'].reduce((map, direction) => {
				map[direction] = null
				return map
			}, {})
		}

		Object.assign(diffs.matchedStart, resetDiffs())
		Object.assign(diffs.matchedEnd, resetDiffs())

		Object.assign(resistanceMap.matchedStart, resetDiffs())
		Object.assign(resistanceMap.matchedEnd, resetDiffs())

		Object.assign(prevDiffs.matchedStart, resetDiffs())
		Object.assign(prevDiffs.matchedEnd, resetDiffs())
	}

	const updateDiffsRelativeToPairedElement = () => {
		currentSlide.value.elements.forEach((element) => {
			const diffFromElement = getDiffFromElement(element)

			const canPair = canElementPair(diffFromElement)
			const isPaired = pairElementId.value == element.id

			if (canPair) pairElement(element.id, diffFromElement)
			else if (isPaired) unpairElement()
		})
	}

	const updateDiffs = () => {
		if (!target.value) return

		// sync previous diffs
		Object.entries(diffs).forEach(([key, value]) => {
			Object.entries(value).forEach(([direction, diff]) => {
				prevDiffs[key][direction] = diff
			})
		})

		updateDiffsRelativeToSlide()

		updateDiffsRelativeToPairedElement()
	}

	const getDynamicThresholds = (axis) => {
		const scaleFactor = 0.1
		const scaledWidth = selectionBounds.width * slideBounds.scale * scaleFactor

		const isCenterAxis = ['centerX', 'centerY'].includes(axis)

		let minThreshold, maxThreshold, maxResistanceThreshold

		if (isCenterAxis) {
			minThreshold = scaledWidth > 50 ? scaledWidth / 6 : scaledWidth / 5
			maxThreshold = scaledWidth > 50 ? scaledWidth / 4 : scaledWidth / 3
			maxResistanceThreshold = 5
		} else {
			minThreshold = scaledWidth > 50 ? scaledWidth / 8 : scaledWidth / 7
			maxThreshold = scaledWidth > 50 ? scaledWidth / 6 : scaledWidth / 5
			maxResistanceThreshold = 3
		}

		return {
			threshold: Math.max(minThreshold, Math.min(maxThreshold, scaledWidth)),
			resistance_threshold: Math.max(1, Math.min(maxResistanceThreshold, scaledWidth * 0.15)),
		}
	}

	const getDiffsForAxis = (axis, point) => {
		let diff, prevDiff

		if (['slideCenterY', 'slideCenterX'].includes(axis)) {
			diff = diffs.slideCenter[point]
			prevDiff = prevDiffs.slideCenter[point]
		}

		return { diff, prevDiff }
	}

	const getThresholdsAndMargin = (axis) => {
		return {
			...getDynamicThresholds(axis),
			margin: ['centerX', 'centerY'].includes(axis) ? 1 : 5,
		}
	}

	const handleSnapMovement = (axis, point) => {
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

		const setGuideMaps = () => {
			const guide = getGuideForDirection(axis)

			const withinResistanceRange = movingAway && Math.abs(diff) < resistance_threshold
			const withinVisibilityRange = Math.abs(diff) < threshold

			resistanceMap[guide] = diff !== null && withinResistanceRange
			visibilityMap[guide] = withinVisibilityRange
		}

		const { diff, prevDiff } = getDiffsForAxis(axis, point)

		const { threshold, resistance_threshold, margin } = getThresholdsAndMargin(axis)

		const movingAway = isMovingAway()

		setGuideMaps()

		let offsetX = 0
		let offsetY = 0
		let offsetWidth = 0

		if (axis == 'slideCenterY') {
			offsetX = getSnapOffset()
		} else if (axis == 'slideCenterX') {
			offsetY = getSnapOffset()
		}

		return {
			offsetX: offsetX,
			offsetY: offsetY,
			offsetWidth: offsetWidth,
		}
	}

	const getCenterOffsets = () => {
		let pointX = 'centerX',
			pointY = 'centerY'

		if (mode.value == 'resizing') {
			if (currentResizer.value.includes('left')) pointX = 'startX'
			else if (currentResizer.value.includes('right')) pointX = 'endX'

			if (currentResizer.value.includes('top')) pointY = 'startY'
			else if (currentResizer.value.includes('bottom')) pointY = 'endY'
		}

		const { offsetX, offsetWidth } = handleSnapMovement('slideCenterX', pointX)

		const { offsetY } = handleSnapMovement('slideCenterY', pointY)

		return {
			centerOffsetX: offsetX,
			centerOffsetWidth: offsetWidth,
			centerOffsetY: offsetY,
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
			pairedOffsetX: getOffset('X').offsetX,
			pairedOffsetY: getOffset('Y').offsetY,
			pairedOffsetWidth: getOffset('X').offsetWidth,
		}
	}

	const getSnapDelta = () => {
		if (!target.value) return

		const { centerOffsetX, centerOffsetY, centerOffsetWidth } = getCenterOffsets()

		const { pairedOffsetX, pairedOffsetY, pairedOffsetWidth } = getPairedOffsets()

		return {
			x: centerOffsetX - pairedOffsetX || 0,
			y: centerOffsetY - pairedOffsetY || 0,
			width: centerOffsetWidth + pairedOffsetWidth || 0,
		}
	}

	const handleSnapping = (interaction = 'dragging') => {
		mode.value = interaction

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

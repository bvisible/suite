import { ref, reactive, computed } from 'vue'
import { selectionBounds, currentSlide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'

export const useSnapping = (target, parent, currentResizer, hasOngoingInteraction) => {
	// element wrt slide center
	const slideCenterAlignmentKeys = ['centerX', 'centerY', 'startX', 'startY', 'endX', 'endY']

	// element wrt other elements
	const matchedAlignmentKeys = ['left', 'right', 'top', 'bottom']

	const initDiffs = () => {
		const makeNullMap = (keys) => {
			const map = {}
			keys.forEach((k) => (map[k] = null))
			return map
		}

		return {
			slideCenter: makeNullMap(slideCenterAlignmentKeys),
			matched: makeNullMap(matchedAlignmentKeys),
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

	const getPointMap = (key) => {
		if (key == 'centerY') {
			return {
				left: 'startX',
				right: 'endX',
				def: 'centerX',
			}
		}

		return {
			top: 'startY',
			bottom: 'endY',
			def: 'centerY',
		}
	}

	const getPointForVisibilityKey = (key) => {
		const pointMap = getPointMap(key)

		let point = pointMap.def

		if (mode.value == 'dragging' || !currentResizer.value) return point

		point =
			pointMap[Object.keys(pointMap).find((key) => currentResizer.value.includes(key))] ||
			point

		return point
	}

	const visibilityMap = computed(() => {
		if (!hasOngoingInteraction.value) return {}

		const keys = ['centerX', 'centerY', 'left', 'right', 'top', 'bottom']

		const map = {}
		keys.forEach((key) => {
			let diff

			if (key == 'centerY') {
				const point = getPointForVisibilityKey(key)
				diff = getDiffsForAxis('slideCenterY', point).diff
			} else if (key == 'centerX') {
				const point = getPointForVisibilityKey(key)
				diff = getDiffsForAxis('slideCenterX', point).diff
			} else {
				diff = diffs.matched[key]
			}
			const threshold = getDynamicThresholds(key).threshold

			map[key] = diff !== null && Math.abs(diff) < threshold
		})

		return map
	})

	const mode = ref(null)

	const getGuideForDirection = (direction) => {
		const guideMap = {
			slideCenterY: 'centerX',
			slideCenterX: 'centerY',
		}
		return guideMap[direction] || direction
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

		diffs.slideCenter.startY =
			getDiffFromCenter('X') + (selectionBounds.height * slideBounds.scale) / 2
		diffs.slideCenter.endY =
			getDiffFromCenter('X') - (selectionBounds.height * slideBounds.scale) / 2
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

		Object.entries(diffFromElement).forEach(([direction, diff]) => {
			diffs.matched[direction] = diff
		})
	}

	const unpairElement = () => {
		pairElementId.value = null

		const resetDiffs = () => {
			return ['left', 'right', 'top', 'bottom'].reduce((map, direction) => {
				map[direction] = null
				return map
			}, {})
		}

		Object.assign(diffs.matched, resetDiffs())
		Object.assign(prevDiffs.matched, resetDiffs())
		Object.assign(resistanceMap, resetDiffs())
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

	const getDynamicMargin = (axis) => {
		if (['centerX', 'centerY'].includes(axis)) {
			return selectionBounds.width * slideBounds.scale * 0.1
		}
		return selectionBounds.height * slideBounds.scale * 0.05
	}

	const getDynamicThresholds = (axis) => {
		const scaleFactor = 0.1
		const scaledHeight = selectionBounds.height * slideBounds.scale * scaleFactor

		const isCenterAxis = ['centerX', 'centerY'].includes(axis)

		let minThreshold, maxThreshold, maxResistanceThreshold

		if (isCenterAxis) {
			minThreshold = scaledHeight > 50 ? scaledHeight / 6 : scaledHeight / 5
			maxThreshold = scaledHeight > 50 ? scaledHeight / 4 : scaledHeight / 3
			maxResistanceThreshold = 5
		} else {
			minThreshold = scaledHeight > 50 ? scaledHeight / 6 : scaledHeight / 5
			maxThreshold = scaledHeight > 50 ? scaledHeight / 4 : scaledHeight / 3
			maxResistanceThreshold = 3
		}

		return {
			threshold: Math.max(minThreshold, Math.min(maxThreshold, scaledHeight)),
			resistance_threshold: Math.max(
				1,
				Math.min(maxResistanceThreshold, scaledHeight * 0.15),
			),
		}
	}

	const getDiffsForAxis = (axis, point) => {
		let diff, prevDiff

		if (['slideCenterY', 'slideCenterX'].includes(axis)) {
			diff = diffs.slideCenter[point]
			prevDiff = prevDiffs.slideCenter[point]
		} else if (['left', 'right', 'top', 'bottom'].includes(axis)) {
			diff = diffs.matched[axis]
			prevDiff = prevDiffs.matched[axis]
		}

		return { diff, prevDiff }
	}

	const getThresholdsAndMargin = (axis) => {
		return {
			...getDynamicThresholds(axis),
			margin: getDynamicMargin(axis),
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
			if (canSnap && !movingAway) {
				return diff
			}
			return 0
		}

		const limitResistanceToOneSide = (activeGuide) => {
			const resizer = currentResizer.value || ''

			const oppositeGuides = {
				left: 'right',
				right: 'left',
				top: 'bottom',
				bottom: 'top',
			}

			Object.entries(oppositeGuides).forEach(([side, opposite]) => {
				if (resizer.includes(side)) {
					resistanceMap[opposite] = false
					resistanceMap['centerX'] = false
					resistanceMap['centerY'] = false
				}
			})
		}

		const setResistanceMap = () => {
			const guide = getGuideForDirection(axis)
			const withinResistanceRange = movingAway && Math.abs(diff) < resistance_threshold
			resistanceMap[guide] = diff !== null && withinResistanceRange

			limitResistanceToOneSide(guide)
		}

		const setResizeSnapOffsets = () => {
			const resizer = currentResizer.value || ''
			const snapOffset = getSnapOffset()

			if (axis == 'right' && resizer.includes('right')) {
				offsetX = 0
				offsetWidth = -snapOffset
			} else if (axis == 'left' && resizer.includes('left')) {
				offsetX = snapOffset
				offsetWidth = snapOffset
			} else if (axis == 'bottom' && resizer.includes('bottom')) {
				offsetY = 0
				offsetWidth = -snapOffset
			} else if (axis == 'top' && resizer.includes('top')) {
				offsetY = snapOffset
				offsetWidth = snapOffset
			}
		}

		const setDragSnapOffsets = () => {
			const snapOffset = getSnapOffset()
			if (['slideCenterY', 'left', 'right'].includes(axis)) {
				offsetX = snapOffset
			} else if (['slideCenterX', 'top', 'bottom'].includes(axis)) {
				offsetY = snapOffset
			}
		}

		const { diff, prevDiff } = getDiffsForAxis(axis, point)

		const { threshold, resistance_threshold, margin } = getThresholdsAndMargin(axis)

		const movingAway = isMovingAway()

		setResistanceMap()

		let offsetX = 0
		let offsetY = 0
		let offsetWidth = 0

		if (mode.value == 'resizing') {
			setResizeSnapOffsets()
		} else {
			setDragSnapOffsets()
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

		const resizer = currentResizer.value || ''

		if (mode.value == 'resizing') {
			if (resizer.includes('left')) pointX = 'startX'
			else if (resizer.includes('right')) pointX = 'endX'

			if (resizer.includes('top')) pointY = 'startY'
			else if (resizer.includes('bottom')) pointY = 'endY'
		}

		const { offsetX, offsetWidth } = handleSnapMovement('slideCenterX', pointX)

		const { offsetY, offsetWidth: offsetWidthY } = handleSnapMovement('slideCenterY', pointY)

		return {
			centerOffsetX: offsetX,
			centerOffsetWidth: offsetWidth + offsetWidthY,
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

		const dragEnd =
			mode.value == 'dragging' &&
			Math.abs(diffs.matched[end]) < Math.abs(diffs.matched[start])
		const resizeEnd =
			mode.value == 'resizing' && currentResizer.value?.includes(end.toLowerCase())

		if (dragEnd || resizeEnd) {
			return handleSnapMovement(end)
		}

		return handleSnapMovement(start)
	}

	const getPairedOffsets = () => {
		const { offsetX, offsetWidth } = getOffset('X')
		const { offsetY, offsetWidth: offsetWidthY } = getOffset('Y')

		return {
			pairedOffsetX: offsetX,
			pairedOffsetY: offsetY,
			pairedOffsetWidth: offsetWidth + offsetWidthY,
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

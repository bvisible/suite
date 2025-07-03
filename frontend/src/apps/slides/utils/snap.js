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

	const getDiffFromCenter = (axis) => {
		if (!target.value) return
		let slideCenter, elementCenter

		if (axis == 'Y') {
			const elementLeft = selectionBounds.left * slideBounds.scale + slideBounds.left
			const elementWidth = selectionBounds.width * slideBounds.scale

			slideCenter = slideBounds.left + slideBounds.width / 2
			elementCenter = elementLeft + elementWidth / 2
		} else {
			const elementTop = selectionBounds.top * slideBounds.scale + slideBounds.top
			const elementHeight = selectionBounds.height * slideBounds.scale

			slideCenter = slideBounds.top + slideBounds.height / 2
			elementCenter = elementTop + elementHeight / 2
		}

		return slideCenter - elementCenter
	}

	const canElementPair = (diffLeft, diffRight, diffTop, diffBottom) => {
		const pairings = {
			left: diffLeft,
			right: diffRight,
			top: diffTop,
			bottom: diffBottom,
		}

		return Object.values(pairings).some((direction, diff) => {
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

	const setPairedDiffs = () => {
		slide.value.elements.forEach((element) => {
			if (activeElementIds.value.includes(element.id)) return

			const elementDiv = document.querySelector(`[data-index="${element.id}"]`)
			if (!elementDiv || !target.value) return

			const elementBounds = elementDiv.getBoundingClientRect()
			const activeBounds = getActiveElementBounds()

			const diffLeft = activeBounds.left - elementBounds.left
			const diffRight = activeBounds.right - elementBounds.right
			const diffTop = activeBounds.top - elementBounds.top
			const diffBottom = activeBounds.bottom - elementBounds.bottom

			const canPair = canElementPair(diffLeft, diffRight, diffTop, diffBottom)
			const isPaired = pairElementId.value == element.id

			if (canPair) {
				pairElementId.value = element.id

				diffs.left = diffLeft
				diffs.right = diffRight
				diffs.top = diffTop
				diffs.bottom = diffBottom
			} else if (isPaired) {
				pairElementId.value = null

				diffs.left = null
				diffs.right = null
				diffs.top = null
				diffs.bottom = null
			}
		})
	}

	const updateGuides = () => {
		if (!target.value) return

		Object.assign(prevDiffs, diffs)

		diffs.centerX = getDiffFromCenter('X')
		diffs.centerY = getDiffFromCenter('Y')

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

	const getPairedOffsets = () => {
		let offsetLeft = 0,
			offsetTop = 0

		if (Math.abs(diffs.right) < Math.abs(diffs.left)) {
			offsetLeft = handleSnapMovement('right')
		} else {
			offsetLeft = handleSnapMovement('left')
		}

		if (Math.abs(diffs.bottom) < Math.abs(diffs.top)) {
			offsetTop = handleSnapMovement('bottom')
		} else {
			offsetTop = handleSnapMovement('top')
		}

		return { offsetLeft, offsetTop }
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

	return {
		visibilityMap,
		resistanceMap,
		updateGuides,
		getSnapDelta,
	}
}

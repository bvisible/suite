import { ref, reactive, computed } from 'vue'
import { selectionBounds, slide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'

export const useSnapping = (target, parent) => {
	const CENTER_PROXIMITY_THRESHOLD = 15
	const PROXIMITY_THRESHOLD = 10

	const snapMovement = ref({ x: 0, y: 0 })

	const hasSnapped = ref(false)
	let snapTimeout = null

	const diffs = reactive({
		vertical: 0,
		horizontal: 0,
		left: 0,
		right: 0,
		top: 0,
		bottom: 0,
	})

	const prevDiffs = reactive({
		vertical: 0,
		horizontal: 0,
		left: 0,
		right: 0,
		top: 0,
		bottom: 0,
	})

	const visibilityMap = computed(() => {
		if (!target.value) return
		return {
			vertical: Math.abs(diffs.vertical) < PROXIMITY_THRESHOLD,
			horizontal: Math.abs(diffs.horizontal) < PROXIMITY_THRESHOLD,
			left: Math.abs(diffs.left) < 10,
			right: Math.abs(diffs.right) < 10,
			top: Math.abs(diffs.top) < 10,
			bottom: Math.abs(diffs.bottom) < 10,
		}
	})

	const getScaledValue = (value, axis) => {
		if (axis == 'X') return (value - slideBounds.left) / slideBounds.scale
		return (value - slideBounds.top) / slideBounds.scale
	}

	const getElementBounds = (div) => {
		const rect = div.getBoundingClientRect()
		return {
			left: getScaledValue(rect.left, 'X'),
			top: getScaledValue(rect.top, 'Y'),
			right: getScaledValue(rect.right, 'X'),
			bottom: getScaledValue(rect.bottom, 'Y'),
			height: rect.height / slideBounds.scale,
			width: rect.width / slideBounds.scale,
		}
	}

	const getDiffFromCenter = (axis) => {
		if (!target.value) return
		let slideCenter, elementCenter

		const activeBounds = getElementBounds(target.value.$el)

		if (axis == 'X') {
			slideCenter = slideBounds.width / 2
			elementCenter = selectionBounds.left + selectionBounds.width / 2
		} else {
			slideCenter = slideBounds.height / 2
			elementCenter = selectionBounds.top + selectionBounds.height / 2
		}

		return slideCenter - elementCenter
	}

	const canElementPair = (diffLeft, diffRight, diffTop, diffBottom) => {
		return (
			Math.abs(diffLeft) < PROXIMITY_THRESHOLD ||
			Math.abs(diffRight) < PROXIMITY_THRESHOLD ||
			Math.abs(diffTop) < PROXIMITY_THRESHOLD ||
			Math.abs(diffBottom) < PROXIMITY_THRESHOLD
		)
	}

	const setPairedDiffs = () => {
		slide.value.elements.forEach((element) => {
			if (activeElementIds.value.includes(element.id)) return

			const elementDiv = document.querySelector(`[data-index="${element.id}"]`)
			if (!elementDiv || !target.value) return

			const activeBounds = selectionBounds
			const elementBounds = getElementBounds(elementDiv)

			const diffLeft = activeBounds.left - elementBounds.left
			const diffRight = activeBounds.left + activeBounds.width - elementBounds.right
			const diffTop = activeBounds.top - elementBounds.top
			const diffBottom = activeBounds.top + activeBounds.height - elementBounds.bottom

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

		prevDiffs.vertical = diffs.vertical
		prevDiffs.horizontal = diffs.horizontal
		prevDiffs.left = diffs.left
		prevDiffs.right = diffs.right
		prevDiffs.top = diffs.top
		prevDiffs.bottom = diffs.bottom

		diffs.vertical = getDiffFromCenter('Y')
		diffs.horizontal = getDiffFromCenter('X')

		setPairedDiffs()
	}

	const getSnapOffset = (axis) => {
		const diff = diffs[axis]
		const prevDiff = prevDiffs[axis]

		let threshold, margin
		if (['horizontal', 'vertical'].includes(axis)) {
			threshold = CENTER_PROXIMITY_THRESHOLD
			margin = 3
		} else {
			threshold = PROXIMITY_THRESHOLD
			margin = 5
		}

		let offset = 0

		const canSnap = Math.abs(diff + threshold) < margin || Math.abs(diff - threshold) < margin
		const movingAway = Math.abs(diff) > Math.abs(prevDiff)

		if (canSnap && !movingAway) {
			offset = diff
		}

		return offset
	}

	const delayNextMovement = () => {
		hasSnapped.value = true

		clearTimeout(snapTimeout)
		snapTimeout = setTimeout(() => {
			hasSnapped.value = false
		}, 450)
	}

	const applySnapMovement = (axis) => {
		let offset = 0

		const possibleOffset = getSnapOffset(axis)

		if (possibleOffset) {
			offset += possibleOffset

			delayNextMovement()
		}

		return offset
	}

	const getCenterOffsets = () => {
		return {
			offsetX: applySnapMovement('horizontal'),
			offsetY: applySnapMovement('vertical'),
		}
	}

	const getPairedOffsets = () => {
		let offsetLeft = 0,
			offsetTop = 0

		if (Math.abs(diffs.right) < Math.abs(diffs.left)) {
			offsetLeft = applySnapMovement('right')
		} else {
			offsetLeft = applySnapMovement('left')
		}

		if (Math.abs(diffs.bottom) < Math.abs(diffs.top)) {
			offsetTop = applySnapMovement('bottom')
		} else {
			offsetTop = applySnapMovement('top')
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
		disableMovement: hasSnapped,
		updateGuides,
		getSnapDelta,
	}
}

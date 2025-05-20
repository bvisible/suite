import { ref, reactive, computed } from 'vue'
import { slide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'

export const useSnapping = (target, parent) => {
	const PROXIMITY_THRESHOLD = 30

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
		const slideBounds = getElementBounds(parent.value)

		if (axis == 'X') {
			slideCenter = slideBounds.left + slideBounds.width / 2
			elementCenter = activeBounds.left + activeBounds.width / 2
		} else {
			slideCenter = slideBounds.top + slideBounds.height / 2
			elementCenter = activeBounds.top + activeBounds.height / 2
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

			const activeBounds = getElementBounds(target.value.$el)
			const elementBounds = getElementBounds(elementDiv)

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

		let offset = 0

		const canSnap =
			Math.abs(diff + PROXIMITY_THRESHOLD) < 3 || Math.abs(diff - PROXIMITY_THRESHOLD) < 3
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

import { ref, reactive, computed } from 'vue'
import { selectionBounds, slide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'

export const useSnapping = (target, parent) => {
	const CENTER_PROXIMITY_THRESHOLD = 40
	const PROXIMITY_THRESHOLD = 8

	const snapMovement = ref({ x: 0, y: 0 })

	const hasSnapped = ref(false)
	let snapTimeout = null

	const diffs = reactive({
		centerX: null,
		centerY: null,
		left: null,
		right: null,
		top: null,
		bottom: null,
	})

	const prevDiffs = reactive({
		centerX: null,
		centerY: null,
		left: null,
		right: null,
		top: null,
		bottom: null,
	})

	const visibilityMap = computed(() => {
		if (!target.value) return
		return {
			centerX: Math.abs(diffs.centerX) < getDynamicThreshold('centerX').threshold,
			centerY: Math.abs(diffs.centerY) < getDynamicThreshold('centerY').threshold,
			left: Math.abs(diffs.left) < PROXIMITY_THRESHOLD,
			right: Math.abs(diffs.right) < PROXIMITY_THRESHOLD,
			top: Math.abs(diffs.top) < PROXIMITY_THRESHOLD,
			bottom: Math.abs(diffs.bottom) < PROXIMITY_THRESHOLD,
		}
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
		return (
			Math.abs(diffLeft) < PROXIMITY_THRESHOLD ||
			Math.abs(diffRight) < PROXIMITY_THRESHOLD ||
			Math.abs(diffTop) < PROXIMITY_THRESHOLD ||
			Math.abs(diffBottom) < PROXIMITY_THRESHOLD
		)
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

	const resistanceMap = reactive({
		X: false,
		Y: false,
	})

	const getDynamicThreshold = (axis) => {
		const scaleFactor = 0.1
		const scaled = selectionBounds.width * slideBounds.scale * scaleFactor
		const minThreshold = ['centerX', 'centerY'].includes(axis) ? scaled / 2 : 5
		const maxThreshold = ['centerX', 'centerY'].includes(axis) ? scaled * 2 : 50

		return {
			threshold: Math.max(minThreshold, Math.min(maxThreshold, scaled)),
			resistance_threshold: scaled * 0.15,
		}
	}

	const getSnapOffset = (axis) => {
		const diff = diffs[axis]
		const prevDiff = prevDiffs[axis]

		let margin
		if (['centerX', 'centerY'].includes(axis)) {
			margin = 1
		} else {
			margin = 3
		}

		const { threshold, resistance_threshold } = getDynamicThreshold(axis)

		let offset = 0

		const canSnap = Math.abs(diff + threshold) < margin || Math.abs(diff - threshold) < margin
		const movingAway =
			Math.abs(diff) >= Math.abs(prevDiff) || Math.abs(prevDiff) - threshold < 1

		const direction = axis == 'centerY' ? 'X' : 'Y'

		if (canSnap && !movingAway) {
			offset = diff
		}

		resistanceMap[direction] =
			diff !== null && movingAway && Math.abs(diff) < resistance_threshold
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
			offsetX: applySnapMovement('centerY'),
			offsetY: applySnapMovement('centerX'),
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
		resistanceMap,
		updateGuides,
		getSnapDelta,
	}
}

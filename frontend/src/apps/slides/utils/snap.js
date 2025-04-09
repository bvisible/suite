import { ref, reactive, computed } from 'vue'

export const useSnapping = (target, parent) => {
	const PROXIMITY_THRESHOLD = 30

	const snapMovement = ref({ x: 0, y: 0 })

	const hasSnapped = ref(false)
	let snapTimeout = null

	const diffs = reactive({
		vertical: 0,
		horizontal: 0,
	})

	const prevDiffs = reactive({
		vertical: 0,
		horizontal: 0,
	})

	const visibilityMap = computed(() => {
		if (!target.value?.$el) return { vertical: false, horizontal: false }

		return {
			vertical: Math.abs(diffs.vertical) < PROXIMITY_THRESHOLD,
			horizontal: Math.abs(diffs.horizontal) < PROXIMITY_THRESHOLD,
		}
	})

	const getElementBounds = (element) => {
		const rect = element.getBoundingClientRect()
		return {
			left: rect.left,
			top: rect.top,
			width: rect.width,
			height: rect.height,
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

	const updateGuides = () => {
		if (!target.value) return

		prevDiffs.vertical = diffs.vertical
		prevDiffs.horizontal = diffs.horizontal

		diffs.vertical = getDiffFromCenter('Y')
		diffs.horizontal = getDiffFromCenter('X')
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

	const getSnapMovement = () => {
		if (!target.value) return

		return {
			x: applySnapMovement('horizontal'),
			y: applySnapMovement('vertical'),
		}
	}

	return {
		visibilityMap,
		disableMovement: hasSnapped,
		updateGuides,
		getSnapMovement,
	}
}

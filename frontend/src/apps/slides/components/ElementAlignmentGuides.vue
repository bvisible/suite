<template>
	<div
		v-for="guide in ['left', 'right', 'top', 'bottom', 'centerX', 'centerY']"
		:key="guide"
		:style="guideStyles[guide]"
	></div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { slide } from '@/stores/slide'
import { activePosition, activeElementId, pairElementId, activeElement } from '@/stores/element'
import { useElementBounding } from '@vueuse/core'

const props = defineProps({
	slideRect: Object,
})

const CENTER_PROXIMITY_THRESHOLD = 20
const PROXIMITY_THRESHOLD = 10

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

const activeDiv = computed(() => {
	return document.querySelector(`[data-index="${activeElementId.value}"]`)
})

const activeRect = useElementBounding(activeDiv)

const pairedDiv = computed(() => {
	return document.querySelector(`[data-index="${pairElementId.value}"]`)
})

const pairedRect = useElementBounding(pairedDiv)

const pairElement = computed(() => {
	return slide.value.elements[pairElementId.value]
})

const snapToCenter = () => {
	if (Math.abs(diffCenterX.value) < CENTER_PROXIMITY_THRESHOLD) {
		const newLeft =
			activeElement.value.left + (diffCenterX.value * 960) / props.slideRect.width.value
		activeElement.value = { ...activeElement.value, left: newLeft }
	}
	if (Math.abs(diffCenterY.value) < CENTER_PROXIMITY_THRESHOLD) {
		const newTop =
			activeElement.value.top + (diffCenterY.value * 960) / props.slideRect.width.value
		activeElement.value = { ...activeElement.value, top: newTop }
	}
}

const snapToPairedElement = () => {
	if (!pairElement.value) return
	let element = { ...activeElement.value }
	const l = Math.abs(diffLeft.value) < PROXIMITY_THRESHOLD ? diffLeft.value : 0
	const r = Math.abs(diffRight.value) < PROXIMITY_THRESHOLD ? diffRight.value : 0
	if (Math.abs(l) > Math.abs(r)) {
		element.left += l
	} else {
		element.left += r
	}

	const t = Math.abs(diffTop.value) < PROXIMITY_THRESHOLD ? diffTop.value : 0
	const b = Math.abs(diffBottom.value) < PROXIMITY_THRESHOLD ? diffBottom.value : 0
	if (Math.abs(t) > Math.abs(b)) {
		element.top += t
	} else {
		element.top += b
	}
	activeElement.value = element
}

const diffCenterX = computed(() => {
	if (!activePosition.value) return
	const rect = activeDiv.value.getBoundingClientRect()
	const centerX = props.slideRect.width.value / 2 + props.slideRect.left.value
	const centerOfElementX = rect.left + rect.width / 2
	return centerX - centerOfElementX
})

const diffCenterY = computed(() => {
	if (!activePosition.value) return
	const rect = activeDiv.value.getBoundingClientRect()
	const centerY = props.slideRect.height.value / 2 + props.slideRect.top.value
	const centerOfElementY = rect.top + rect.height / 2
	return centerY - centerOfElementY
})

const diffLeft = computed(() => {
	if (!pairElement.value) return
	return pairElement.value.left - activeElement.value.left
})

const diffRight = computed(() => {
	if (!pairElement.value) return
	return (
		pairElement.value.left +
		pairElement.value.width -
		activeElement.value.left -
		activeElement.value.width
	)
})

const diffTop = computed(() => {
	if (!pairElement.value) return
	return pairElement.value.top - activeElement.value.top
})

const diffBottom = computed(() => {
	if (!pairElement.value) return
	const currentScale = props.slideRect.width.value / 960
	const ogHeight = activeRect.height.value / currentScale
	const ogPairedHeight = pairedRect.height.value / currentScale
	const pairedElementBottom = pairElement.value.top + ogPairedHeight
	const activeElementBottom = activeElement.value.top + ogHeight
	return pairedElementBottom - activeElementBottom
})

const commonGuideStyles = {
	position: 'fixed',
	borderColor: '#70b6f092',
	borderStyle: 'dashed',
}

const leftGuideStyles = computed(() => {
	if (diffLeft.value == undefined || Math.abs(diffLeft.value) > PROXIMITY_THRESHOLD) return ''
	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left - 6.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const rightGuideStyles = computed(() => {
	if (diffRight.value == undefined || Math.abs(diffRight.value) > PROXIMITY_THRESHOLD) return ''
	return {
		...commonGuideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left + activeElement.value.width + 5.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const topGuideStyles = computed(() => {
	if (diffTop.value == undefined || Math.abs(diffTop.value) > PROXIMITY_THRESHOLD) return ''
	return {
		...commonGuideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top - 6.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const bottomGuideStyles = computed(() => {
	if (diffBottom.value == undefined || Math.abs(diffBottom.value) > PROXIMITY_THRESHOLD) return ''
	const currentScale = props.slideRect.width.value / 960
	const originalHeight = activeRect.height.value / currentScale
	return {
		...commonGuideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top + originalHeight + 5.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const centerXGuideStyles = computed(() => {
	if (Math.abs(diffCenterX.value) > CENTER_PROXIMITY_THRESHOLD) return ''
	return {
		backgroundColor: '#70b6f092',
		height: '100%',
		width: '1px',
		position: 'fixed',
		left: `${props.slideRect.width.value / 2}px`,
	}
})

const centerYGuideStyles = computed(() => {
	if (Math.abs(diffCenterX.value) > CENTER_PROXIMITY_THRESHOLD) return ''
	return {
		backgroundColor: '#70b6f092',
		width: '100%',
		height: '1px',
		position: 'fixed',
		top: `${props.slideRect.height.value / 2}px`,
	}
})

const setCurrentPairedDataIndex = () => {
	if (!activeElement.value) return
	let i = null
	slide.value.elements.forEach((element, index) => {
		if (index == activeElementId.value) return
		let diffLeft = Math.abs(element.left - activeElement.value.left)
		let diffRight = Math.abs(
			element.left + element.width - activeElement.value.left - activeElement.value.width,
		)
		let diffTop = Math.abs(element.top - activeElement.value.top)
		let elementDiv = document.querySelector(`[data-index="${index}"]`).getBoundingClientRect()
		let diffBottom = Math.abs(
			elementDiv.top + elementDiv.height - activeRect.top.value - activeRect.height.value,
		)
		if ([diffLeft, diffRight, diffTop, diffBottom].some((diff) => diff < PROXIMITY_THRESHOLD))
			i = index
	})
	pairElementId.value = i
}

watch(
	() => activePosition.value,
	() => {
		if (!activePosition.value) return
		setCurrentPairedDataIndex()
		snapToCenter()
		snapToPairedElement()
	},
	{ immediate: true },
)
</script>

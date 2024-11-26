<template>
	<div
		v-show="Math.abs(diffCenterX) < 10"
		class="absolute left-1/2 h-full w-[1px] -translate-x-1/2 bg-blue-400"
	></div>

	<div
		v-show="Math.abs(diffCenterY) < 10"
		class="absolute top-1/2 h-[1px] w-full -translate-y-1/2 bg-blue-400"
	></div>

	<div v-show="diffLeft < 10" :style="leftGuideStyles"></div>
	<div v-show="diffRight < 10" :style="rightGuideStyles"></div>
	<div v-show="diffTop < 10" :style="topGuideStyles"></div>
	<div v-show="diffBottom < 10" :style="bottomGuideStyles"></div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
	position,
	activeElement,
	currentDataIndex,
	activeSlideElements,
	currentPairedDataIndex,
} from '@/stores/slide'
import { useElementBounding } from '@vueuse/core'

const props = defineProps({
	slideRect: Object,
})

const activeDiv = computed(() => {
	return document.querySelector(`[data-index="${currentDataIndex.value}"]`)
})

const activeRect = useElementBounding(activeDiv)

const pairedDiv = computed(() => {
	return document.querySelector(`[data-index="${currentPairedDataIndex.value}"]`)
})

const pairedRect = useElementBounding(pairedDiv)

const pairElement = computed(() => {
	return activeSlideElements.value[currentPairedDataIndex.value]
})

const snapToCenter = () => {
	if (Math.abs(diffCenterX.value) < 10) {
		activeElement.value.left += diffCenterX.value
	}
	if (Math.abs(diffCenterY.value) < 10) {
		activeElement.value.top += diffCenterY.value
	}
}

const snapToPairElement = () => {
	if (!pairElement.value) return
	if (diffLeft.value < 10) {
		activeElement.value.left = pairElement.value.left
	}
	if (diffRight.value < 10) {
		activeElement.value.left =
			pairElement.value.left + pairElement.value.width - activeElement.value.width
	}
	if (diffTop.value < 10) {
		activeElement.value.top = pairElement.value.top
	}
	if (diffBottom.value < 10) {
		activeElement.value.top =
			pairElement.value.top + pairedRect.height.value - activeRect.height.value
	}
}

const diffCenterX = computed(() => {
	if (!position.value) return
	let centerX = props.slideRect.left.value + props.slideRect.width.value / 2
	let centerOfElementX = position.value.left + activeRect.width.value / 2
	return centerX - centerOfElementX
})

const diffCenterY = computed(() => {
	if (!position.value) return
	let centerY = props.slideRect.top.value + props.slideRect.height.value / 2
	let centerOfElementY = position.value.top + activeRect.height.value / 2
	return centerY - centerOfElementY
})

const diffLeft = computed(() => {
	if (!pairElement.value) return
	return Math.abs(pairElement.value.left - activeElement.value.left)
})

const diffRight = computed(() => {
	if (!pairElement.value) return
	return Math.abs(
		pairElement.value.left +
			pairElement.value.width -
			activeElement.value.left -
			activeElement.value.width,
	)
})

const diffTop = computed(() => {
	if (!pairElement.value) return
	return Math.abs(pairElement.value.top - activeElement.value.top)
})

const diffBottom = computed(() => {
	if (!pairElement.value) return
	return Math.abs(
		pairElement.value.top +
			pairedRect.height.value -
			activeElement.value.top -
			activeRect.height.value,
	)
})

const guideStyles = {
	position: 'fixed',
	borderColor: '#70b6f0',
	borderStyle: 'dashed',
}

const leftGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left - 5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const rightGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '0 0 0 1px',
		left: `${activeElement.value.left + activeElement.value.width + 4.5}px`,
		top: `${Math.min(pairElement.value.top, activeElement.value.top)}px`,
		height: `${Math.abs(pairElement.value.top - activeElement.value.top)}px`,
	}
})

const topGuideStyles = computed(() => {
	if (!pairElement.value) return
	return {
		...guideStyles,
		borderWidth: '1px 0 0 0',
		top: `${activeElement.value.top - 5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
})

const bottomGuideStyles = computed(() => {
	if (!pairElement.value) return
	let a = {
		...guideStyles,
		borderWidth: '1px 0 0 0',
		top: `${pairedRect.top.value + pairedRect.height.value - props.slideRect.top.value + 4.5}px`,
		left: `${Math.min(pairElement.value.left, activeElement.value.left)}px`,
		width: `${Math.abs(pairElement.value.left - activeElement.value.left)}px`,
	}
	return a
})

const setCurrentPairedDataIndex = () => {
	if (!activeElement.value) return
	let i = null
	activeSlideElements.value.forEach((element, index) => {
		if (index == currentDataIndex.value) return
		let diffLeft = Math.abs(element.left - activeElement.value.left)
		let diffRight = Math.abs(
			element.left + element.width - activeElement.value.left - activeElement.value.width,
		)
		let diffTop = Math.abs(element.top - activeElement.value.top)
		let elementDiv = document.querySelector(`[data-index="${index}"]`).getBoundingClientRect()
		let diffBottom = Math.abs(
			elementDiv.top + elementDiv.height - activeRect.top.value - activeRect.height.value,
		)
		if (diffLeft < 10 || diffRight < 10 || diffTop < 10 || diffBottom < 10) i = index
	})
	currentPairedDataIndex.value = i
}

watch(
	() => position.value,
	() => {
		if (!position.value) return
		setCurrentPairedDataIndex()
		snapToCenter()
		snapToPairElement()
	},
	{ immediate: true },
)
</script>

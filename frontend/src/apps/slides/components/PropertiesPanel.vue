<template>
	<div v-if="presentation.data" class="flex w-64 flex-col border-l bg-white" @wheel.prevent>
		<div v-if="activeElement">
			<CollapsibleSection title="Alignment" :initialState="true">
				<template #default>
					<div class="flex items-center gap-3">
						<NumberInput
							v-model="selectionBounds.left"
							prefix="x"
							:rangeStart="0"
							:rangeStep="1"
							:hideButtons="true"
						/>
						<NumberInput
							v-model="selectionBounds.top"
							prefix="y"
							:rangeStart="0"
							:rangeStep="1"
							:hideButtons="true"
						/>
					</div>

					<div :class="fieldLabelClasses">Horizontal</div>
					<div class="grid grid-cols-3 gap-3">
						<div
							:class="getAlignmentButtonClasses('left')"
							@click="performAlignment('left')"
						>
							<AlignStartVertical size="18" :strokeWidth="1.5" />
						</div>
						<div
							:class="getAlignmentButtonClasses('centerX')"
							@click="performAlignment('centerX')"
						>
							<AlignCenterVertical size="18" :strokeWidth="1.5" />
						</div>
						<div
							:class="getAlignmentButtonClasses('right')"
							@click="performAlignment('right')"
						>
							<AlignEndVertical size="18" :strokeWidth="1.5" />
						</div>
					</div>

					<div :class="fieldLabelClasses">Vertical</div>
					<div class="grid grid-cols-3 gap-3">
						<div :class="getAlignmentButtonClasses('top')">
							<AlignStartHorizontal size="18" :strokeWidth="1.5" />
						</div>
						<div :class="getAlignmentButtonClasses('centerY')">
							<AlignCenterHorizontal size="18" :strokeWidth="1.5" />
						</div>
						<div :class="getAlignmentButtonClasses('bottom')">
							<AlignEndHorizontal size="18" :strokeWidth="1.5" />
						</div>
					</div>
				</template>
			</CollapsibleSection>
		</div>

		<component :is="activeProperties" />

		<div v-if="activeElement">
			<CollapsibleSection title="Other">
				<template #default>
					<SliderInput
						label="Opacity"
						:rangeStart="0"
						:rangeEnd="100"
						:modelValue="parseFloat(activeElement.opacity) || 100"
						@update:modelValue="(value) => (activeElement.opacity = value)"
					/>
				</template>
			</CollapsibleSection>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { FormControl } from 'frappe-ui'

import {
	AlignStartVertical,
	AlignCenterVertical,
	AlignEndVertical,
	AlignStartHorizontal,
	AlignCenterHorizontal,
	AlignEndHorizontal,
} from 'lucide-vue-next'

import SlideProperties from '@/components/SlideProperties.vue'
import TextProperties from '@/components/TextProperties.vue'
import ImageProperties from '@/components/ImageProperties.vue'
import VideoProperties from '@/components/VideoProperties.vue'

import SliderInput from '@/components/controls/SliderInput.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { presentation } from '@/stores/presentation'
import { slide, selectionBounds, slideBounds } from '@/stores/slide'
import { activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

const activeProperties = computed(() => {
	const elementType = activeElement.value?.type

	if (!elementType) return SlideProperties

	if (elementType == 'text') return TextProperties
	if (elementType == 'image') return ImageProperties
	if (elementType == 'video') return VideoProperties
})

const isAligned = (direction) => {
	if (direction === 'left') return Math.round(selectionBounds.left) == 0
	if (direction === 'centerX') {
		return (
			Math.round(selectionBounds.left + selectionBounds.width / 2) ==
			Math.round(slideBounds.width / (2 * slideBounds.scale))
		)
	}
	if (direction === 'right') {
		return (
			Math.round(slideBounds.width / slideBounds.scale) ==
			Math.round(selectionBounds.left + selectionBounds.width)
		)
	}
	if (direction === 'top') return Math.round(selectionBounds.top) == 0
	if (direction === 'centerY') {
		return (
			Math.round(selectionBounds.top + selectionBounds.height / 2) ==
			Math.round(slideBounds.height / (2 * slideBounds.scale))
		)
	}
	if (direction === 'bottom') {
		return (
			Math.round(slideBounds.height / slideBounds.scale) ==
			Math.round(selectionBounds.top + selectionBounds.height)
		)
	}
	return false
}

const getAlignmentButtonClasses = (direction) => {
	const baseClasses =
		'flex cursor-pointer items-center justify-center rounded border py-1.5 hover:border-gray-400'
	const activeClasses = isAligned(direction)
		? 'border-gray-500 text-gray-900'
		: 'text-gray-600 hover:text-gray-700'
	return `${baseClasses} ${activeClasses}`
}

const performAlignment = (direction) => {
	if (direction === 'left') {
		selectionBounds.left = 0
	} else if (direction === 'centerX') {
		selectionBounds.left =
			Math.round(slideBounds.width / (2 * slideBounds.scale)) -
			Math.round(selectionBounds.width / 2)
	} else if (direction === 'right') {
		selectionBounds.left =
			Math.round(slideBounds.width / slideBounds.scale) - Math.round(selectionBounds.width)
	}
}
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>

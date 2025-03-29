<template>
	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Orientation</div>
		<div
			v-for="(direction, index) in imageOrientationProperties"
			:key="index"
			class="flex cursor-pointer items-center justify-between"
			@click="toggleImageOrientation(direction)"
		>
			<div class="text-sm text-gray-600">{{ direction.label }}</div>
			<component :is="direction.icon" size="20" :strokeWidth="1.2" />
		</div>
	</div>
</template>

<script setup>
import { FlipHorizontal, FlipVertical } from 'lucide-vue-next'

import { activeElement } from '@/stores/element'
import { sectionClasses, sectionTitleClasses } from '@/utils/constants'

const imageOrientationProperties = [
	{
		property: 'invertX',
		label: 'Flip Horizontal',
		icon: FlipHorizontal,
	},
	{
		property: 'invertY',
		label: 'Flip Vertical',
		icon: FlipVertical,
	},
]

const toggleImageOrientation = (direction) => {
	activeElement.value[direction.property] = activeElement.value[direction.property] === 1 ? -1 : 1
}
</script>

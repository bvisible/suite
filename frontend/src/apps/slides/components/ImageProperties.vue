<template>
	<CollapsibleSection title="Orientation" :initialState="true">
		<template #default>
			<div
				v-for="(direction, index) in imageOrientationProperties"
				:key="index"
				class="flex cursor-pointer items-center justify-between"
				@click="toggleImageOrientation(direction)"
			>
				<div :class="fieldLabelClasses">{{ direction.label }}</div>
				<component :is="direction.icon" size="20" :strokeWidth="1.2" />
			</div>
		</template>
	</CollapsibleSection>

	<MediaProperties />
</template>

<script setup>
import { FlipHorizontal, FlipVertical } from 'lucide-vue-next'

import MediaProperties from '@/components/MediaProperties.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

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
	const currentValue = activeElement.value[direction.property]
	let newValue = 1
	if (!currentValue || currentValue == 1) newValue = -1
	activeElement.value[direction.property] = newValue
}
</script>

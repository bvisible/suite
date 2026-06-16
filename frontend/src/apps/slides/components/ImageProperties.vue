<template>
	<CollapsibleSection title="Orientation">
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

import MediaProperties from '@/apps/slides/components/MediaProperties.vue'
import CollapsibleSection from '@/apps/slides/components/controls/CollapsibleSection.vue'

import { activeElement } from '@/apps/slides/stores/element'
import { fieldLabelClasses } from '@/apps/slides/utils/constants'
import { inject } from 'vue'

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

const setProperty = inject('setProperty')

const toggleImageOrientation = (direction) => {
	const currentValue = activeElement.value[direction.property]
	let newValue = 1
	if (!currentValue || currentValue == 1) newValue = -1
	setProperty(direction.property, newValue)
}
</script>

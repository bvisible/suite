<template>
	<CollapsibleSection title="Appearance">
		<template #default>
			<SliderInput
				v-if="activeElement.type == 'text'"
				label="Opacity"
				:rangeStart="0"
				:rangeEnd="100"
				:modelValue="parseFloat(editorStyles.opacity)"
				@update:modelValue="(value) => updateProperty('opacity', parseFloat(value))"
			/>
			<SliderInput
				v-else
				label="Opacity"
				:rangeStart="0"
				:rangeEnd="100"
				v-model="activeElement.opacity"
				@sliderdown="onOpacityUpdateStart"
				@sliderup="onOpacityUpdateEnd"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { inject } from 'vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'
import SliderInput from '@/components/controls/SliderInput.vue'

import { currentSlide } from '@/stores/slide'
import { activeElement, activeElementIds } from '@/stores/element'
import { useTextEditor } from '@/composables/useTextEditor'
import { useDeferredCommit } from '@/composables/useDeferredCommit'
import { editElementCommand } from '@/stores/commands'

const { editorStyles, updateProperty } = useTextEditor()

const setProperty = inject('setProperty')

const setOpacity = (value) => {
	setProperty('opacity', parseFloat(value))
}

const { onStart: onOpacityUpdateStart, onEnd: onOpacityUpdateEnd } = useDeferredCommit(
	() => activeElement.value.opacity,
	(oldValue, newValue) =>
		editElementCommand({
			slideId: currentSlide.value?.clientId,
			elementIds: activeElementIds.value,
			property: 'opacity',
			oldValue,
			newValue,
		}),
)
</script>

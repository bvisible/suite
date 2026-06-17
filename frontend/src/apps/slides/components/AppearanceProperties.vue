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

import { useTextEditor } from '@/composables/useTextEditor'

import { activeElement } from '@/stores/element'

const setPropertyDeferred = inject('setPropertyDeferred')

const { editorStyles, updateProperty } = useTextEditor()

const { onStart: onOpacityUpdateStart, onEnd: onOpacityUpdateEnd } = setPropertyDeferred(
	'element',
	'opacity',
)
</script>

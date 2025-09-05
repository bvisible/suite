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
				:modelValue="activeElement.opacity"
				@update:modelValue="(value) => setOpacity(value)"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'
import SliderInput from '@/components/controls/SliderInput.vue'

import { activeElement } from '@/stores/element'
import { useTextEditor } from '@/composables/useTextEditor'

const { editorStyles, updateProperty } = useTextEditor()

const setOpacity = (value) => {
	activeElement.value['opacity'] = parseFloat(value)
}
</script>

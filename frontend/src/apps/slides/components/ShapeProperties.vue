<template>
	<CollapsibleSection title="Style">
		<template #default>
			<div
				class="flex items-center justify-between"
				v-if="activeElement.shapeType == 'rectangle'"
			>
				<div :class="fieldLabelClasses">Border Radius</div>
				<div class="w-28">
					<NumberInput
						:modelValue="activeElement.borderRadius"
						@update:modelValue="(val) => setProperty('borderRadius', val)"
						suffix="px"
						:rangeStart="0"
						:rangeEnd="50"
						:rangeStep="0.5"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Stroke Width</div>
				<div class="w-28">
					<NumberInput
						:modelValue="activeElement.strokeWidth"
						@update:modelValue="(val) => setProperty('strokeWidth', val)"
						suffix="px"
						:rangeStart="0"
						:rangeEnd="50"
						:rangeStep="0.5"
					/>
				</div>
			</div>

			<div v-if="activeElement.shapeType != 'line'" class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Fill Color</div>
				<ColorPicker
					v-model="activeElement.fillColor"
					@colordown="onFillColorUpdateStart"
					@colorup="onFillColorUpdateEnd"
				/>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Stroke Color</div>

				<ColorPicker
					v-model="activeElement.strokeColor"
					@colordown="onStrokeColorUpdateStart"
					@colorup="onStrokeColorUpdateEnd"
				/>
			</div>
		</template>
	</CollapsibleSection>

	<ShadowProperties />
</template>

<script setup>
import { inject } from 'vue'

import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ShadowProperties from '@/components/ShadowProperties.vue'

import { activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

const setProperty = inject('setProperty')
const setPropertyDeferred = inject('setPropertyDeferred')

const { onStart: onFillColorUpdateStart, onEnd: onFillColorUpdateEnd } = setPropertyDeferred(
	'element',
	'fillColor',
)

const { onStart: onStrokeColorUpdateStart, onEnd: onStrokeColorUpdateEnd } = setPropertyDeferred(
	'element',
	'strokeColor',
)
</script>

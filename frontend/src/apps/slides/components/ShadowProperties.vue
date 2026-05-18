<template>
	<CollapsibleSection title="Shadow" :initialState="false">
		<template #default>
			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Color</div>
				<ColorPicker
					class="pe-[0.2px]"
					v-model="activeElement.shadowColor"
					@colordown="onShadowColorUpdateStart"
					@colorup="onShadowColorUpdateEnd"
				/>
			</div>

			<SliderInput
				label="Spread"
				:rangeStart="0"
				:rangeEnd="500"
				v-model="activeElement.shadowSpread"
				@sliderdown="onShadowSpreadUpdateStart"
				@sliderup="onShadowSpreadUpdateEnd"
			/>

			<SliderInput
				label="Offset X"
				:rangeStart="-50"
				:rangeEnd="50"
				v-model="activeElement.shadowOffsetX"
				@sliderdown="onShadowOffsetXUpdateStart"
				@sliderup="onShadowOffsetXUpdateEnd"
			/>

			<SliderInput
				label="Offset Y"
				:rangeStart="-50"
				:rangeEnd="50"
				v-model="activeElement.shadowOffsetY"
				@sliderdown="onShadowOffsetYUpdateStart"
				@sliderup="onShadowOffsetYUpdateEnd"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { inject, watch } from 'vue'

import SliderInput from '@/components/controls/SliderInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

const setPropertyDeferred = inject('setPropertyDeferred')

const shadowDefaults = {
	shadowColor: '#000000ff',
	shadowSpread: 0,
	shadowOffsetX: 0,
	shadowOffsetY: 0,
}

watch(
	activeElement,
	(element) => {
		if (!element) return
		Object.entries(shadowDefaults).forEach(([property, value]) => {
			if (element[property] == null) {
				element[property] = value
			}
		})
	},
	{ immediate: true },
)

const { onStart: onShadowColorUpdateStart, onEnd: onShadowColorUpdateEnd } = setPropertyDeferred(
	'element',
	'shadowColor',
)

const { onStart: onShadowSpreadUpdateStart, onEnd: onShadowSpreadUpdateEnd } = setPropertyDeferred(
	'element',
	'shadowSpread',
)

const { onStart: onShadowOffsetXUpdateStart, onEnd: onShadowOffsetXUpdateEnd } =
	setPropertyDeferred('element', 'shadowOffsetX')

const { onStart: onShadowOffsetYUpdateStart, onEnd: onShadowOffsetYUpdateEnd } =
	setPropertyDeferred('element', 'shadowOffsetY')
</script>

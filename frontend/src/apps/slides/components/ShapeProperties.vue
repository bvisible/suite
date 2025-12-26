<template>
	<CollapsibleSection title="Style">
		<template #default>
			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Fill Color</div>
				<ColorPicker class="pe-[0.2px]" v-model="activeElement.fillColor" />
			</div>

			<div
				class="flex items-center justify-between"
				v-if="activeElement.shapeType == 'rectangle'"
			>
				<div :class="fieldLabelClasses">Border Radius</div>
				<div class="w-28">
					<NumberInput
						v-model="activeElement.borderRadius"
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
						v-model="activeElement.strokeWidth"
						suffix="px"
						:rangeStart="0"
						:rangeEnd="50"
						:rangeStep="0.5"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Stroke Color</div>
				<ColorPicker class="pe-[0.2px]" v-model="activeElement.strokeColor" />
			</div>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import NumberInput from '@/components/controls/NumberInput.vue'

import { activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'
</script>

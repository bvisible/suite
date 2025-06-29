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
						<div :class="quickAlignmentButtonClasses">
							<AlignStartVertical size="18" :strokeWidth="1.5" />
						</div>
						<div :class="quickAlignmentButtonClasses">
							<AlignCenterVertical size="18" :strokeWidth="1.5" />
						</div>
						<div :class="quickAlignmentButtonClasses">
							<AlignEndVertical size="18" :strokeWidth="1.5" />
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

import { AlignStartVertical, AlignCenterVertical, AlignEndVertical } from 'lucide-vue-next'

import SlideProperties from '@/components/SlideProperties.vue'
import TextProperties from '@/components/TextProperties.vue'
import ImageProperties from '@/components/ImageProperties.vue'
import VideoProperties from '@/components/VideoProperties.vue'

import SliderInput from '@/components/controls/SliderInput.vue'
import CollapsibleSection from './controls/CollapsibleSection.vue'

import { presentation } from '@/stores/presentation'
import { slide, selectionBounds } from '@/stores/slide'
import { activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

const activeProperties = computed(() => {
	const elementType = activeElement.value?.type

	if (!elementType) return SlideProperties

	if (elementType == 'text') return TextProperties
	if (elementType == 'image') return ImageProperties
	if (elementType == 'video') return VideoProperties
})

const quickAlignmentButtonClasses =
	'flex cursor-pointer items-center justify-center rounded border py-1.5 text-gray-600'
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>

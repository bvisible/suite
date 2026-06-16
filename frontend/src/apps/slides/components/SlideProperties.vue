<template>
	<div :class="sectionClasses">
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<div :class="sectionTitleClasses">Slide</div>
				<div class="pe-0.5 text-2xs-semibold text-gray-700">
					{{ slideIndex + 1 + ' of ' + slides.length }}
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Background Color</div>
				<ColorPicker
					v-model="currentSlide.background"
					@colordown="onBgUpdateStart"
					@colorup="onBgUpdateEnd"
				/>
			</div>
		</div>
	</div>

	<CollapsibleSection title="Transition">
		<template #default>
			<Select
				:options="['Magic Move', 'Fade', 'Slide In', 'None']"
				:modelValue="currentSlide.transition"
				@update:modelValue="(option) => setSlideTransition(option)"
			/>

			<SliderInput
				v-show="currentSlide.transition && currentSlide.transition != 'None'"
				label="Duration"
				:rangeStart="0"
				:rangeEnd="4"
				:rangeStep="0.1"
				:modelValue="parseFloat(currentSlide.transitionDuration)"
				@update:modelValue="(value) => setTransitionAttribute('transitionDuration', value)"
				@sliderdown="onTransitionUpdateStart"
				@sliderup="onTransitionUpdateEnd"
			/>

			<div
				class="flex items-center justify-between"
				v-if="currentSlide.transition == 'Magic Move'"
			>
				<div :class="fieldLabelClasses">Fade In Other Elements</div>

				<Checkbox
					size="sm"
					class="cursor-pointer px-1"
					:modelValue="currentSlide.fadeUnmatchedElements"
					@update:modelValue="(v) => setTransitionAttribute('fadeUnmatchedElements', v)"
				/>
			</div>

			<Button
				label="Apply To All Slides"
				variant="outline"
				class="text-sm"
				@click="applyTransitionToAllSlides"
			>
				<template #prefix>
					<LucideCheckCheck class="size-3.5 stroke-[1.5]" />
				</template>
			</Button>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { inject } from 'vue'
import { Select, Checkbox, toast } from 'frappe-ui'

import { slides, slideIndex, currentSlide } from '@/apps/slides/stores/slide'
import { sectionClasses, sectionTitleClasses, fieldLabelClasses } from '@/apps/slides/utils/constants'
import { getCommandsToAddMagicMove, getCommandsToRemoveMagicMove } from '@/apps/slides/stores/transition'

import SliderInput from '@/apps/slides/components/controls/SliderInput.vue'
import ColorPicker from '@/apps/slides/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/apps/slides/components/controls/CollapsibleSection.vue'
import { editSlideCommand, batchCommand } from '@/apps/slides/stores/commands'
import { commandHistory } from '@/apps/slides/stores/historyMeta'

const setPropertyDeferred = inject('setPropertyDeferred')

const setSlideTransition = (option) => {
	const duration = option == 'None' ? 0 : 1
	const slide = currentSlide.value

	let commands = []

	commands.push(
		editSlideCommand({
			slideId: currentSlide.value.clientId,
			property: 'transition',
			oldValue: currentSlide.value.transition,
			newValue: option,
		}),
	)

	commands.push(
		editSlideCommand({
			slideId: currentSlide.value.clientId,
			property: 'transitionDuration',
			oldValue: currentSlide.value.transitionDuration,
			newValue: duration,
		}),
	)

	commands.push(
		editSlideCommand({
			slideId: currentSlide.value.clientId,
			property: 'fadeUnmatchedElements',
			oldValue: currentSlide.value.fadeUnmatchedElements,
			newValue: option == 'Magic Move',
		}),
	)

	if (option == 'Magic Move') {
		commands = commands.concat(getCommandsToAddMagicMove(slideIndex.value) || [])
	} else {
		commands = commands.concat(getCommandsToRemoveMagicMove(slideIndex.value) || [])
	}

	commandHistory.execute(
		batchCommand({
			slideId: currentSlide.value.clientId,
			elementIds: [],
			commands,
		}),
	)
}

const setTransitionAttribute = (property, value) => {
	currentSlide.value[property] = value
}

const applyTransitionToAllSlides = () => {
	const sourceSlide = currentSlide.value
	const commands = []

	slides.value.forEach((slide, index) => {
		if (index !== slideIndex.value) {
			commands.push(
				editSlideCommand({
					slideId: slide.clientId,
					property: 'transition',
					oldValue: slide.transition,
					newValue: sourceSlide.transition,
				}),
			)

			commands.push(
				editSlideCommand({
					slideId: slide.clientId,
					property: 'transitionDuration',
					oldValue: slide.transitionDuration,
					newValue: sourceSlide.transitionDuration,
				}),
			)

			commands.push(
				editSlideCommand({
					slideId: slide.clientId,
					property: 'fadeUnmatchedElements',
					oldValue: slide.fadeUnmatchedElements,
					newValue: sourceSlide.fadeUnmatchedElements,
				}),
			)

			if (sourceSlide.transition == 'Magic Move') {
				commands.push(...(getCommandsToAddMagicMove(index) || []))
			} else {
				commands.push(...(getCommandsToRemoveMagicMove(index) || []))
			}
		}
	})

	commandHistory.execute(
		batchCommand({
			slideId: sourceSlide.clientId,
			elementIds: [],
			commands,
		}),
	)

	toast.success('Applied transition to all slides')
}

const { onStart: onBgUpdateStart, onEnd: onBgUpdateEnd } = setPropertyDeferred(
	'slide',
	'background',
)

const { onStart: onTransitionUpdateStart, onEnd: onTransitionUpdateEnd } = setPropertyDeferred(
	'slide',
	'transitionDuration',
)
</script>

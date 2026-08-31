<template>
	<Section label="Appearance">
		<NumberControl
			v-if="activeElement.type == 'text'"
			:modelValue="textOpacity"
			label="Opacity"
			suffix="%"
			:min="0"
			:max="100"
			:max-digits="3"
			:step="1"
			@update:modelValue="(value) => updateProperty('opacity', parseFloat(value))"
		/>
		<NumberControl
			v-else
			:modelValue="activeElement.opacity"
			label="Opacity"
			suffix="%"
			:min="0"
			:max="100"
			:max-digits="3"
			:step="1"
			@update:modelValue="opacity.set"
			@change-start="opacity.begin"
			@change-end="opacity.commit"
		/>
	</Section>
</template>

<script setup>
import { computed } from 'vue'

import NumberControl from '@/apps/slides/components/controls/NumberControl.vue'
import Section from '@/apps/slides/components/controls/Section.vue'

import { useTextEditor } from '@/apps/slides/composables/useTextEditor'
import { useElementProperty } from '@/apps/slides/composables/editProperty'

import { activeElement } from '@/apps/slides/stores/element'

const { editorStyles, updateProperty } = useTextEditor()

const opacity = useElementProperty('opacity')

const textOpacity = computed(() => {
	const value = parseFloat(editorStyles.opacity)
	return Number.isNaN(value) ? 100 : value
})
</script>

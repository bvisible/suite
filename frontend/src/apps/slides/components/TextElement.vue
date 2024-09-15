<template>
	<div
		class="relative"
		:style="{
			width: elementStyle.width,
			left: elementStyle.left,
			height: unref(rect.height) + 'px',
			top: elementStyle.top,
		}"
	>
		<div
			ref="textElement"
			class="textElement focus:outline-none focus:ring-[1.5px] focus:ring-[#808080]/50"
			:style="elementStyle"
			:contenteditable="element.isContentEditable"
		>
			{{ element.content }}
		</div>
		<Resizer v-if="activeElement == element" :element="element" :isResizing="isResizing" />
	</div>
</template>

<script setup>
import { computed, ref, unref, useTemplateRef } from 'vue'
import { useElementBounding } from '@vueuse/core'
import Resizer from './Resizer.vue'
import { activeElement } from '@/stores/slide'

const props = defineProps({
	active: Boolean,
	inSlideShow: Boolean,
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const el = useTemplateRef('textElement')

const rect = useElementBounding(el)

const elementStyle = computed(() => ({
	padding: '5px',
	position: 'fixed',
	width: element.value.width,
	height: 'auto',
	left: props.inSlideShow ? parseInt(element.value.left) * 2.29 + 'px' : element.value.left,
	top: props.inSlideShow ? parseInt(element.value.top) * 2.81 + 'px' : element.value.top,
	content: element.value.content,
	fontFamily: element.value.fontFamily,
	fontSize: element.value.fontSize + 'px',
	fontWeight: element.value.fontWeight,
	fontStyle: element.value.fontStyle,
	textDecoration: element.value.textDecoration,
	textTransform: element.value.textTransform,
	userSelect: element.value.isContentEditable ? 'text' : 'none',
	cursor: element.value.isDragging
		? 'move'
		: element.value.isContentEditable
			? 'text'
			: 'default',
	opacity: element.value.opacity / 100,
	lineHeight: element.value.lineHeight + 'px',
	letterSpacing: element.value.letterSpacing + 'px',
	wordWrap: 'break-word',
}))

const isResizing = ref(false)
</script>

<template>
	<div
		ref="textElement"
		class="textElement focus:outline-none"
		:style="elementStyle"
		:contenteditable="element.isContentEditable"
		@dblclick="makeElementEditable($event, element)"
		@blur="handleBlur($event, element)"
		:class="isEqual(activeElement, element) ? 'outline outline-offset-2 outline-blue-400' : ''"
	>
		{{ element.content }}
	</div>
</template>

<script setup>
import { computed, ref, unref, useTemplateRef } from 'vue'
import { useElementBounding } from '@vueuse/core'
import Resizer from './Resizer.vue'
import { activeElement, inSlideShow } from '@/stores/slide'
import { isEqual } from 'lodash'

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
	position: 'fixed',
	width: `${element.value.width}px`,
	height: 'auto',
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	content: element.value.content,
	fontFamily: element.value.fontFamily,
	fontSize: element.value.fontSize + 'px',
	fontWeight: element.value.fontWeight,
	fontStyle: element.value.fontStyle,
	textDecoration: element.value.textDecoration,
	textTransform: element.value.textTransform,
	userSelect: element.value.isContentEditable ? 'text' : 'none',
	opacity: element.value.opacity / 100,
	lineHeight: element.value.lineHeight,
	letterSpacing: element.value.letterSpacing + 'px',
	wordWrap: 'break-word',
	textAlign: element.value.textAlign,
	color: element.value.color,
}))

const makeElementEditable = (e, element) => {
	if (inSlideShow.value) return
	e.stopPropagation()
	element.isContentEditable = true
}

const handleBlur = (e, element) => {
	element.isContentEditable = false
	element.content = e.target.innerText
}
</script>

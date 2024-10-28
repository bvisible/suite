<template>
	<div
		:contenteditable="element.isContentEditable"
		:style="textStyle"
		@dblclick="makeElementEditable($event, element)"
		@blur="handleBlur($event, element)"
	>
		{{ element.content }}
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { inSlideShow } from '@/stores/slide'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const textStyle = computed(() => ({
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

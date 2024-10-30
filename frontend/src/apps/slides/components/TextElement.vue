<template>
	<div
		class="focus:outline-none"
		:contenteditable="isEqual(focusedElement, element)"
		:style="textStyle"
		@click="selectElement"
	>
		{{ element.content }}
	</div>
</template>

<script setup>
import { isEqual } from 'lodash'
import { ref, computed, inject } from 'vue'
import { activeElement, focusedElement, inSlideShow } from '@/stores/slide'
import { handleSingleAndDoubleClick } from '@/utils/clickHandler'

const setActiveElement = inject('setActiveElement')
const removeDragAndResize = inject('removeDragAndResize')

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
	userSelect: focusedElement.value == element.value ? 'text' : 'none',
	opacity: element.value.opacity / 100,
	lineHeight: element.value.lineHeight,
	letterSpacing: element.value.letterSpacing + 'px',
	wordWrap: 'break-word',
	textAlign: element.value.textAlign,
	color: element.value.color,
	cursor: focusedElement.value == element.value ? 'text' : '',
}))

const selectElement = (e) => {
	if (inSlideShow.value) return
	handleSingleAndDoubleClick(e, setActiveText, setFocusElement)
}

const setActiveText = (e) => {
	if (textStyle.value.userSelect == 'text') return
	setActiveElement(e, element.value)
}

const setFocusElement = (e) => {
	e.stopPropagation()
	if (activeElement.value == element.value) removeDragAndResize()
	activeElement.value = element.value
	focusedElement.value = element.value
}
</script>

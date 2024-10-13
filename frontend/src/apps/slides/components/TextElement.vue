<template>
	<div
		class="fixed"
		:style="{
			width: elementStyle.width,
			left: elementStyle.left,
			height: unref(rect.height) + 'px',
			top: elementStyle.top,
			outline: isEqual(activeElement, element) ? '1px solid #70B6F0' : 'none',
		}"
	>
		<div
			ref="textElement"
			class="textElement focus:outline-none"
			:style="elementStyle"
			:contenteditable="element.isContentEditable"
			@dblclick="makeElementEditable($event, element)"
			@blur="handleBlur($event, element)"
		>
			{{ element.content }}
		</div>
		<Resizer
			v-if="isEqual(activeElement, element)"
			:element="element"
			:isResizing="isResizing"
			:resizeHeight="false"
		/>
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
	padding: '5px',
	position: 'fixed',
	width: element.value.width,
	height: 'auto',
	left: element.value.left + 'px',
	top: element.value.top + 'px',
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

const isResizing = ref(false)

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

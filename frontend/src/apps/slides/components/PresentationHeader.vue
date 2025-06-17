<template>
	<div class="flex text-base justify-center items-center">
		<div
			ref="titleInput"
			:contenteditable="editingTitle"
			spellcheck="false"
			:class="inputClasses"
			@click="makeTitleEditable"
			@focus="setCursorPosition"
			@blur="saveTitle"
		>
			{{ presentation.data?.title }}
		</div>
	</div>
</template>

<script setup>
import { ref, useTemplateRef, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { call } from 'frappe-ui'

import { presentation } from '@/stores/presentation'

const route = useRoute()
const router = useRouter()

const titleInputRef = useTemplateRef('titleInput')
const editingTitle = ref(false)

const inputClasses = [
	'max-w-42',
	'w-fit',
	'p-1',
	'text-base',
	'outline-none',
	'font-medium',
	'text-gray-800',
	'cursor-text',
]

const makeTitleEditable = (e) => {
	if (editingTitle.value) return
	editingTitle.value = true
	e.target.focus()
	e.target.tabIndex = 0
	setCursorPosition(e)
}

const setCursorPosition = (e) => {
	const range = document.createRange()
	const selection = window.getSelection()

	range.selectNodeContents(e.target)
	// set cursor to end of text
	range.collapse(false)

	selection.removeAllRanges()
	selection.addRange(range)
}

const renamePresentationDoc = async (newName) => {
	return await call('slides.slides.doctype.presentation.presentation.rename_presentation', {
		name: route.params.presentationId,
		new_name: newName,
	})
}

const saveTitle = async (e) => {
	editingTitle.value = false
	const newTitle = e.target.innerText.trim()

	if (newTitle && newTitle != presentation.data.title) {
		let nameSlug = await renamePresentationDoc(newTitle)
		router.replace({
			name: 'PresentationEditor',
			params: { presentationId: nameSlug },
		})
	}
}
</script>

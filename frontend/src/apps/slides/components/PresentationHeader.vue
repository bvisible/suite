<template>
	<div
		:class="inputClasses"
		:contenteditable="editingTitle"
		spellcheck="false"
		@click="makeTitleEditable"
		@focus="setCursorPositionAtEnd"
		@blur="saveTitle"
		@keydown.enter.prevent
	>
		{{ presentation.data?.title }}
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { call } from 'frappe-ui'

import { presentation, updatePresentationTitle } from '@/stores/presentation'
import { setCursorPositionAtEnd } from '@/utils/helpers'

const route = useRoute()
const router = useRouter()

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
}

const saveTitle = async (e) => {
	editingTitle.value = false

	const newTitle = e.target.innerText.trim()

	if (newTitle && newTitle != presentation.data.title) {
		const slug = await updatePresentationTitle(route.params.presentationId, newTitle)
		router.replace({
			name: 'PresentationEditor',
			params: { presentationId: route.params.presentationId, slug: slug },
		})
	}
}
</script>

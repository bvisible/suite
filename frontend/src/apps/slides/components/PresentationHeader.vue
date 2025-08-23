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
		{{ title }}
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { call } from 'frappe-ui'

import { updatePresentationTitle } from '@/stores/presentation'
import { setCursorPositionAtEnd } from '@/utils/helpers'

const props = defineProps({
	title: String,
})

const route = useRoute()
const router = useRouter()

const editingTitle = ref(false)

const inputClasses = computed(() => {
	const baseClasses = [
		'p-1 px-2',
		'text-base font-medium cursor-text',
		'outline-none rounded-sm',
		'focus:ring-1 focus:ring-gray-400',
		'transition ease-in-out duration-400',
		'whitespace-nowrap',
	]
	if (editingTitle.value) {
		return [...baseClasses, 'text-gray-800', 'max-w-[500px]']
	} else {
		return [...baseClasses, 'truncate', 'max-w-[500px]']
	}
})

const makeTitleEditable = (e) => {
	if (editingTitle.value) return

	editingTitle.value = true
	e.target.focus()
	e.target.tabIndex = 0
}

const saveTitle = async (e) => {
	editingTitle.value = false

	const newTitle = e.target.innerText.trim()

	if (!newTitle) {
		e.target.innerText = props.title
		return
	}

	if (newTitle != props.title) {
		const slug = await updatePresentationTitle(route.params.presentationId, newTitle)
		router.replace({
			name: 'PresentationEditor',
			params: { presentationId: route.params.presentationId, slug: slug },
		})
	}
}
</script>

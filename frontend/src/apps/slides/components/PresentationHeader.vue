<template>
	<div class="flex text-base justify-center items-center">
		<input
			v-if="editingTitle"
			ref="titleInput"
			v-model="newTitle"
			:class="inputClasses"
			spellcheck="false"
			@blur="saveTitle"
		/>
		<div
			v-else
			class="select-none font-semibold text-gray-700 flex items-center"
			@click="makeTitleEditable"
		>
			<div>{{ presentation.data?.title }}</div>
			<div class="text-gray-400 text-xs" v-if="slideDirty">*</div>
		</div>
	</div>
</template>

<script setup>
import { ref, useTemplateRef, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { call } from 'frappe-ui'

import { presentation } from '@/stores/presentation'
import { slideDirty } from '@/stores/slide'

const route = useRoute()
const router = useRouter()

const titleInputRef = useTemplateRef('titleInput')
const newTitle = ref('')
const editingTitle = ref(false)

const inputClasses = [
	'max-w-42',
	'rounded-sm',
	'border-none',
	'py-1',
	'text-base',
	'font-semibold',
	'text-gray-700',
	'focus:ring-[1.5px]',
	'focus:ring-gray-300',
	'focus:ring-offset-1',
]

const makeTitleEditable = () => {
	editingTitle.value = true
	newTitle.value = presentation.data.title
	nextTick(() => titleInputRef.value.focus())
}

const renamePresentationDoc = async (newName) => {
	return await call('slides.slides.doctype.presentation.presentation.rename_presentation', {
		name: route.params.presentationId,
		new_name: newName,
	})
}

const saveTitle = async () => {
	if (newTitle.value && newTitle.value != presentation.data.title) {
		let nameSlug = await renamePresentationDoc(newTitle.value)
		router.replace({
			name: 'PresentationEditor',
			params: { presentationId: nameSlug },
		})
	}
	editingTitle.value = false
}
</script>

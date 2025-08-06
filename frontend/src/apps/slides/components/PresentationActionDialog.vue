<template>
	<Dialog class="pb-0" :options="{ size: 'sm' }">
		<template #body-title>
			<div class="font-semibold">{{ dialogAction }} Presentation</div>
		</template>
		<template #body-content>
			<FormControl
				ref="inputRef"
				v-if="['Duplicate', 'Rename'].includes(dialogAction)"
				:type="'text'"
				size="md"
				variant="subtle"
				label="Presentation Title"
				v-model="newPresentationTitle"
			/>
			<div v-else class="text-base">
				This action will permanently delete
				<strong>{{ presentation?.title }}</strong
				>. Are you sure you want to continue?
			</div>
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				:theme="dialogAction == 'Delete' ? 'red' : 'gray'"
				:label="actions[dialogAction].label"
				@click="performAction()"
			>
				<template #prefix>
					<component :is="actions[dialogAction].icon" size="14" class="stroke-[1.5]" />
				</template>
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, watch, nextTick, useTemplateRef } from 'vue'

import { Dialog, FormControl, call } from 'frappe-ui'

import { createPresentationResource, updatePresentationTitle } from '@/stores/presentation'

import { Copy, Trash, PenLine } from 'lucide-vue-next'

const props = defineProps({
	presentation: Object,
	dialogAction: String,
})

const emit = defineEmits(['reloadList', 'navigate', 'closeDialog'])

const inputRef = useTemplateRef('inputRef')

const newPresentationTitle = ref('')

const actions = {
	Duplicate: {
		label: 'Create Copy',
		icon: Copy,
	},
	Rename: {
		label: 'Update Title',
		icon: PenLine,
	},
	Delete: {
		label: 'Delete Presentation',
		icon: Trash,
	},
}

const performAction = async () => {
	const action = props.dialogAction

	if (!props.dialogAction || !props.presentation) return

	emit('closeDialog')

	let newPresentationId
	switch (action) {
		case 'Rename':
			await renamePresentation()
			break
		case 'Delete':
			await deletePresentation()
			break
		default:
			newPresentationId = await duplicatePresentation()
			break
	}

	if (newPresentationId) {
		emit('navigate', newPresentationId)
	} else {
		emit('reloadList')
	}
}

const duplicatePresentation = async () => {
	return await createPresentationResource.submit({
		title: newPresentationTitle.value,
		duplicateFrom: props.presentation.name,
	})
}

const deletePresentation = async () => {
	await call('slides.slides.doctype.presentation.presentation.delete_presentation', {
		name: props.presentation.name,
	})
}

const renamePresentation = async () => {
	await updatePresentationTitle(props.presentation.name, newPresentationTitle.value)
}

watch(
	() => [props.dialogAction, props.presentation],
	(val) => {
		if (!val) return
		let newTitle
		switch (props.dialogAction) {
			case 'Duplicate':
				newTitle = `Copy of ${props.presentation.title}`
				break
			case 'Rename':
				newTitle = props.presentation.title
				break
			default:
				newTitle = ''
				break
		}

		newPresentationTitle.value = newTitle
		nextTick(() => {
			document.querySelector('input')?.focus()
		})
	},
)
</script>

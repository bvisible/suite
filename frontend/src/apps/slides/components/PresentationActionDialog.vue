<template>
	<Dialog class="pb-0" :options="{ size: 'sm' }">
		<template #body-title>
			<div class="font-semibold">{{ dialogAction }} Presentation</div>
		</template>
		<template #body-content>
			<div v-if="['Duplicate', 'Create'].includes(dialogAction)">
				<FormControl
					:type="'text'"
					size="md"
					variant="subtle"
					label="Presentation Title"
					v-model="newPresentationTitle"
				/>
				<ErrorMessage class="mx-1 mt-2" :message="errorMessage" />
			</div>

			<div v-else class="px-2 text-base">
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
				@click="actions[dialogAction].onClick"
			>
				<template #prefix>
					<component :is="actions[dialogAction].icon" size="14" class="stroke-[1.5]" />
				</template>
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

import { Dialog, FormControl, ErrorMessage, call } from 'frappe-ui'

import { Save, Copy, Trash } from 'lucide-vue-next'

const props = defineProps({
	presentation: Object,
	dialogAction: String,
})

const emit = defineEmits(['reloadList', 'navigate'])

const newPresentationTitle = ref('')
const errorMessage = ref('')

const actions = {
	Create: {
		label: 'Create Presentation',
		icon: Save,
		onClick: () => addPresentation(),
	},
	Duplicate: {
		label: 'Create Copy',
		icon: Copy,
		onClick: () => addPresentation(true),
	},
	Delete: {
		label: 'Delete Presentation',
		icon: Trash,
		onClick: () => deletePresentation(),
	},
}

const createPresentationDoc = async (duplicate) => {
	try {
		return await call('slides.slides.doctype.presentation.presentation.create_presentation', {
			title: newPresentationTitle.value,
			duplicate_from: duplicate ? props.presentation.name : null,
		})
	} catch (DuplicateEntryError) {
		errorMessage.value = 'A presentation with this name already exists.'
	}
}

const addPresentation = async (duplicate) => {
	const presentation = await createPresentationDoc(duplicate)
	if (presentation) {
		errorMessage.value = ''
		emit('navigate', presentation.name)
	}
}

const deletePresentation = async () => {
	await call('slides.slides.doctype.presentation.presentation.delete_presentation', {
		name: props.presentation.name,
	})
	emit('reloadList', true)
}

watch(
	() => props.dialogAction,
	(val) => {
		if (!val) return
		newPresentationTitle.value = ''
		if (props.dialogAction == 'Duplicate') {
			newPresentationTitle.value = `Copy of ${props.presentation.title}`
		}
	},
)
</script>

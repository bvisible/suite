<template>
	<Dialog class="pb-0" :options="{ size: 'sm' }">
		<template #body-title>
			<div class="font-semibold">{{ dialogAction }} Presentation</div>
		</template>
		<template #body-content>
			<FormControl
				v-if="dialogAction == 'Duplicate'"
				:type="'text'"
				size="md"
				variant="subtle"
				label="Presentation Title"
				v-model="newPresentationTitle"
			/>
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

import { Dialog, FormControl, call } from 'frappe-ui'

import { createPresentationResource } from '@/stores/presentation'

import { Save, Copy, Trash } from 'lucide-vue-next'

const props = defineProps({
	presentation: Object,
	dialogAction: String,
})

const emit = defineEmits(['reloadList', 'navigate'])

const newPresentationTitle = ref('')

const actions = {
	Duplicate: {
		label: 'Create Copy',
		icon: Copy,
		onClick: () => duplicatePresentation(),
	},
	Delete: {
		label: 'Delete Presentation',
		icon: Trash,
		onClick: () => deletePresentation(),
	},
}

const duplicatePresentation = async () => {
	emit('closeDialog')
	const presentation = await createPresentationResource.submit({
		title: newPresentationTitle.value,
		duplicateFrom: props.presentation.name,
	})
	if (presentation) {
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

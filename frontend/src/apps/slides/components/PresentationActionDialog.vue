<template>
	<Dialog class="pb-0" :options="{ size: 'sm' }">
		<template #body-title>
			<div class="font-semibold">{{ dialogAction }} Presentation</div>
		</template>
		<template #body-content>
			<FormControl
				v-if="['Duplicate', 'Create'].includes(dialogAction)"
				:type="'text'"
				size="md"
				variant="subtle"
				label="Presentation Title"
				v-model="newPresentationTitle"
			/>
			<div v-else class="text-base px-2">
				This action will permanently delete
				<strong>{{ presentationTitle }}</strong
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

import { Dialog, FormControl } from 'frappe-ui'

import { Save, Copy, Trash } from 'lucide-vue-next'

const props = defineProps({
	presentationTitle: String,
	dialogAction: String,
})

const emit = defineEmits(['create', 'duplicate', 'delete'])

const newPresentationTitle = ref('')

const actions = {
	Create: {
		label: 'Create Presentation',
		icon: Save,
		onClick: () => emit('create', newPresentationTitle.value),
	},
	Duplicate: {
		label: 'Create Copy',
		icon: Copy,
		onClick: () => emit('duplicate', newPresentationTitle.value),
	},
	Delete: {
		label: 'Delete Presentation',
		icon: Trash,
		onClick: () => emit('delete'),
	},
}

watch(
	() => props.dialogAction,
	(val) => {
		if (val) {
			newPresentationTitle.value = ''
			if (props.dialogAction == 'Duplicate') {
				newPresentationTitle.value = `Copy of ${props.presentationTitle}`
			}
		}
	},
)
</script>

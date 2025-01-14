<template>
	<Dialog class="pb-0" v-model="showDialog" :options="{ size: 'sm' }">
		<template #body>
			<div class="flex flex-col gap-6 p-6">
				<div class="flex items-center justify-between">
					<div class="text-md font-semibold text-gray-900">
						{{ dialogAction }} Presentation
					</div>
					<FeatherIcon name="x" class="h-4 cursor-pointer" @click="showDialog = false" />
				</div>
				<FormControl
					v-if="['Rename', 'Duplicate', 'Create'].includes(dialogAction)"
					:type="'text'"
					size="md"
					variant="subtle"
					placeholder="Presentation Title"
					v-model="newPresentationTitle"
				/>
				<div v-else class="text-base">
					Are you sure you want to delete this presentation?
				</div>

				<Button
					v-if="dialogAction == 'Rename'"
					variant="solid"
					label="Update"
					@click="renamePresentation"
				>
					<template #prefix>
						<FeatherIcon name="edit" class="h-3.5" />
					</template>
				</Button>

				<Button
					v-else-if="dialogAction == 'Duplicate'"
					variant="solid"
					label="Create Copy"
					@click="createPresentation('Duplicate')"
				>
					<template #prefix>
						<FeatherIcon name="copy" class="h-3.5" />
					</template>
				</Button>

				<Button
					v-else-if="dialogAction == 'Delete'"
					variant="solid"
					theme="red"
					label="Confirm Deletion"
					@click="deletePresentation"
				>
					<template #prefix>
						<FeatherIcon name="trash" class="h-3.5" />
					</template>
				</Button>

				<Button v-else variant="solid" label="Create" @click="createPresentation('Create')">
					<template #prefix>
						<FeatherIcon name="save" class="h-3.5" />
					</template>
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Dialog, FormControl, call } from 'frappe-ui'
import { presentationList } from '@/stores/presentation'

const router = useRouter()
const showDialog = ref(false)

const dialogAction = defineModel('dialogAction', {
	type: String,
	default: '',
})

const previewPresentation = defineModel('previewPresentation', {
	type: Object,
})

const newPresentationTitle = ref('')

const createPresentation = async (action) => {
	let presentation = null
	showDialog.value = false
	if (action == 'Duplicate') {
		presentation = await call(
			'slides.slides.doctype.presentation.presentation.duplicate_presentation',
			{
				title: newPresentationTitle.value,
				presentation_name: previewPresentation.value.name,
			},
		)
	} else {
		presentation = await call(
			'slides.slides.doctype.presentation.presentation.create_presentation',
			{
				title: newPresentationTitle.value,
			},
		)
	}
	await router.push(`/${presentation.name}`)
}

const renamePresentation = async () => {
	showDialog.value = false
	await call('slides.slides.doctype.presentation.presentation.rename_presentation', {
		name: previewPresentation.value.name,
		new_name: newPresentationTitle.value,
	})
	await presentationList.reload()
	previewPresentation.value.title = newPresentationTitle.value
}

const deletePresentation = async () => {
	showDialog.value = false
	await call('slides.slides.doctype.presentation.presentation.delete_presentation', {
		name: previewPresentation.value.name,
	})
	await presentationList.reload()
	previewPresentation.value = null
}

watch(
	() => dialogAction.value,
	(action) => {
		if (!action) return
		if (action == 'Rename') {
			newPresentationTitle.value = previewPresentation.value.title
		} else if (action == 'Duplicate') {
			newPresentationTitle.value = `Copy of ${previewPresentation.value.title}`
		} else {
			newPresentationTitle.value = ''
		}
		showDialog.value = true
	},
	{ immediate: true },
)
</script>

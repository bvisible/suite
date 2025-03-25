<template>
	<Button
		:icon-left="['Trash', 'Spam'].includes(currentFolder) ? 'trash-2' : 'edit'"
		@click="performAction()"
	>
		{{ buttonMessage }}
	</Button>

	<SendMailModal v-model="showSendModal" @reload-mails="emit('reloadMails', 'Drafts')" />
	<Dialog v-model="showConfirmDialog" :options="confirmDialogOptions" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'

import SendMailModal from '@/components/Modals/SendMailModal.vue'

import type { Folder } from '@/types'

const { currentFolder } = defineProps<{ currentFolder: Folder }>()

const emit = defineEmits(['reloadMails'])

const showSendModal = ref(false)
const showConfirmDialog = ref(false)

const buttonMessage = computed(() => {
	if (currentFolder === 'Trash') return __('Empty Trash')
	if (currentFolder === 'Spam') return __('Empty Spam')
	return __('Compose')
})

const confirmDialogOptions = computed(() => ({
	title: `${buttonMessage.value}?`,
	message: __('This action cannot be undone.'),
	icon: { name: 'alert-triangle', appearance: 'warning' },
	actions: [
		{
			label: __('Confirm'),
			variant: 'solid',
			onClick: () => {
				emptyFolder.submit()
				showConfirmDialog.value = false
			},
		},
	],
}))

const performAction = () => {
	if (['Trash', 'Spam'].includes(currentFolder)) showConfirmDialog.value = true
	else showSendModal.value = true
}

const emptyFolder = createResource({
	url: 'mail.api.mail.empty_folder',
	makeParams: () => ({ folder: currentFolder }),
	onSuccess: () => emit('reloadMails'),
})
</script>

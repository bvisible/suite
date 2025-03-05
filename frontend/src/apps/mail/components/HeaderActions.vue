<template>
	<div>
		<Button
			:icon-left="currentFolder === 'Trash' ? 'trash-2' : 'edit'"
			@click="performAction()"
		>
			{{ __(currentFolder === 'Trash' ? 'Empty Trash' : 'Compose') }}
		</Button>
	</div>
	<SendMailModal v-model="showSendModal" @reload-mails="emit('reloadMails', 'Drafts')" />
	<Dialog v-model="showConfirmDialog" :options="confirmDialogOptions" />
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'

import SendMailModal from '@/components/Modals/SendMailModal.vue'

import type { Folder } from '@/types'

const props = defineProps<{ currentFolder: Folder }>()

const emit = defineEmits(['reloadMails'])

const showSendModal = ref(false)
const showConfirmDialog = ref(false)

const performAction = () => {
	if (props.currentFolder === 'Trash') showConfirmDialog.value = true
	else showSendModal.value = true
}

const emptyTrash = createResource({
	url: 'mail.api.mail.empty_trash',
	onSuccess: () => emit('reloadMails'),
})

const confirmDialogOptions = {
	title: __('Empty Trash?'),
	message: __('This action cannot be undone.'),
	icon: { name: 'alert-triangle', appearance: 'warning' },
	actions: [
		{
			label: __('Confirm'),
			variant: 'solid',
			onClick: () => {
				emptyTrash.submit()
				showConfirmDialog.value = false
			},
		},
	],
}
</script>

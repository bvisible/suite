<template>
	<Button
		:icon-left="['trash', 'junk'].includes(mailbox) ? 'trash-2' : 'edit'"
		@click="performAction()"
	>
		{{ buttonMessage }}
	</Button>

	<SendMail v-model="showSendModal" @reload-mails="emit('reloadMails', 'Drafts')" />
	<Dialog v-model="showConfirmDialog" :options="confirmDialogOptions" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'

import SendMail from '@/components/SendMail.vue'

const { mailbox } = defineProps<{ mailbox: string }>()

const emit = defineEmits(['reloadMails'])

const showSendModal = ref(false)
const showConfirmDialog = ref(false)

const buttonMessage = computed(() => {
	if (mailbox === 'trash') return __('Empty Trash')
	if (mailbox === 'junk') return __('Empty Spam')
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
				emptyMailbox.submit()
				showConfirmDialog.value = false
			},
		},
	],
}))

const performAction = () => {
	if (['trash', 'junk'].includes(mailbox)) showConfirmDialog.value = true
	else showSendModal.value = true
}

const emptyMailbox = createResource({
	url: 'mail.api.mail.empty_mailbox',
	makeParams: () => ({ mailbox }),
	onSuccess: () => emit('reloadMails'),
})
</script>

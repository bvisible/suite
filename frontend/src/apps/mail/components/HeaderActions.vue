<template>
	<div class="flex space-x-2">
		<Button icon="search" variant="ghost" @click="showSearchModal = true" />
		<Button
			:icon-left="[mailboxIds.trash, mailboxIds.junk].includes(mailbox) ? 'trash-2' : 'edit'"
			@click="performAction()"
		>
			{{ buttonMessage }}
		</Button>
	</div>

	<SendMail v-model="showSendModal" />
	<SearchModal v-model="showSearchModal" />
	<Dialog v-model="showConfirmDialog" :options="confirmDialogOptions" />
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'

import { userStore } from '@/stores/user'
import SearchModal from '@/components/Modals/SearchModal.vue'
import SendMail from '@/components/SendMail.vue'

const { mailbox } = defineProps<{ mailbox: string }>()

const emit = defineEmits(['reloadMails'])

const { mailboxIds } = userStore()

const showSearchModal = ref(false)
const showSendModal = ref(false)
const showConfirmDialog = ref(false)

const buttonMessage = computed(() => {
	if (mailbox === mailboxIds.trash) return __('Empty Trash')
	if (mailbox === mailboxIds.junk) return __('Empty Spam')
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
	if ([mailboxIds.trash, mailboxIds.junk].includes(mailbox)) showConfirmDialog.value = true
	else showSendModal.value = true
}

const emptyMailbox = createResource({
	url: 'mail.api.mail.empty_mailbox',
	makeParams: () => ({ mailbox }),
	onSuccess: () => emit('reloadMails'),
})

const handleKeydown = (event: KeyboardEvent) => {
	if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
		event.preventDefault()
		showSearchModal.value = true
	}
}

onMounted(() => document.addEventListener('keydown', handleKeydown))
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))
</script>

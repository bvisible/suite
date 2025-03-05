<template>
	<div>
		<Button
			:icon-left="currentFolder === 'Trash' ? 'trash-2' : 'edit'"
			@click="performAction()"
		>
			{{ __(currentFolder === 'Trash' ? 'Empty Trash' : 'Compose') }}
		</Button>
	</div>
	<SendMailModal v-model="showSendModal" @reload-mails="emit('reloadMails')" />
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Button, createResource } from 'frappe-ui'

import SendMailModal from '@/components/Modals/SendMailModal.vue'

import type { Folder } from '@/types'

const props = defineProps<{ currentFolder: Folder }>()

const emit = defineEmits(['reloadMails'])

const showSendModal = ref(false)

const performAction = () => {
	if (props.currentFolder === 'Trash') emptyTrash.submit()
	else showSendModal.value = true
}

const emptyTrash = createResource({
	url: 'mail.api.mail.empty_trash',
	onSuccess: () => emit('reloadMails'),
})
</script>

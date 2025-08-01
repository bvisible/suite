<template>
	<Dialog
		v-if="account?.doc"
		v-model="show"
		:options="{
			title: accountID,
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					disabled: JSON.stringify(account.doc) === JSON.stringify(account.originalDoc),
					onClick: account.save.submit,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<Switch v-model="account.doc.enabled" :label="__('Enabled')" class="switch" />
				<Switch
					v-model="account.doc.create_mail_contact"
					:label="__('Create Mail Contact')"
					class="switch"
				/>
				<AutocompleteControl
					v-model="account.doc.default_outgoing_email"
					:label="__('Default Email')"
					:show-search="false"
					:options="userAddresses.data"
				/>
				<FormControl v-model="account.doc.display_name" :label="__('Display Name')" />
				<FormControl v-model="account.doc.reply_to" :label="__('Reply To')" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog, FormControl, Switch, createDocumentResource, createResource } from 'frappe-ui'

import { raiseToast } from '@/utils'
import AutocompleteControl from '@/components/Controls/AutocompleteControl.vue'

import type { MailAccount } from '@/types'

const show = defineModel<boolean>()
const { accountID } = defineProps<{ accountID: string }>()

const account = ref()

const getAccount = () =>
	createDocumentResource({
		doctype: 'Mail Account',
		name: accountID,
		transform: (data: MailAccount) => {
			for (const d of ['enabled', 'create_mail_contact']) data[d] = !!data[d]
		},
		setValue: {
			onSuccess: () => {
				show.value = false
				raiseToast(__('Account settings saved successfully'))
			},
			onError: (error) => {
				raiseToast(error.messages[0], 'error')
				account.value.reload()
			},
		},
	})

const userAddresses = createResource({
	url: 'mail.api.admin.get_user_addresses',
	makeParams: () => ({ user: accountID }),
})

watch(
	show,
	(val) => {
		if (!val) return
		account.value = getAccount()
		userAddresses.reload()
	},
	{ immediate: true },
)
</script>

<style>
.switch {
	@apply hover:bg-surface-white active:bg-surface-white cursor-auto !p-0;
}
</style>

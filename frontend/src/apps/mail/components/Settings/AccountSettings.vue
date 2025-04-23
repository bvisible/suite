<template>
	<template v-if="account.doc">
		<h1>{{ __('Outgoing') }}</h1>
		<AutocompleteControl
			v-model="account.doc.default_outgoing_email"
			:label="__('Send Mails From')"
			:show-search="false"
			:options="userAddresses.data"
		/>
		<FormControl v-model="account.doc.display_name" :label="__('Display Name')" />
		<Switch
			v-model="account.doc.track_outgoing_mail"
			:label="__('Track Outgoing Mails')"
			:description="__('Track recipient activity on mails sent by you.')"
		/>
		<Switch
			v-model="account.doc.create_mail_contact"
			:label="__('Create Mail Contacts')"
			:description="__('Create contacts of people you send mails to.')"
		/>

		<h1>{{ __('Incoming') }}</h1>
		<Switch
			v-model="setCustomReplyTo"
			:label="__('Set Custom Reply-To')"
			:description="__('Replies will go to the addresses you specify.')"
			@update:model-value="account.doc.reply_to = null"
		/>
		<FormControl
			v-if="setCustomReplyTo"
			v-model="account.doc.reply_to"
			:label="__('Receive Replies On')"
			placeholder="<John Doe> johndoe@example.com, <John> john@example.io"
			:description="
				__('Enter comma-separated email addresses where replies should be sent.')
			"
		/>

		<h1>{{ __('Recovery') }}</h1>
		<FormControl
			v-model="account.doc.backup_email"
			:label="__('Backup Email')"
			:description="__(`We'll contact you here if there's an issue with your main account.`)"
		/>
		<ErrorMessage :message="account.save.error" />
		<Button
			:label="__('Save Changes')"
			variant="solid"
			:disabled="JSON.stringify(account.doc) === JSON.stringify(account.originalDoc)"
			:loading="account.save.loading"
			class="min-h-7"
			@click="account.save.submit"
		/>
	</template>
</template>

<script setup lang="ts">
import { inject, ref } from 'vue'
import {
	Button,
	ErrorMessage,
	FormControl,
	Switch,
	createDocumentResource,
	createResource,
} from 'frappe-ui'

import { raiseToast } from '@/utils'
import AutocompleteControl from '@/components/Controls/AutocompleteControl.vue'

import type { MailAccount } from '@/types/doctypes'

const user = inject('$user')

const account = createDocumentResource({
	doctype: 'Mail Account',
	name: user.data?.name,
	transform(data: MailAccount) {
		const keys = ['enabled', 'track_outgoing_mail', 'create_mail_contact'] as const
		for (const key of keys) data[key] = !!data[key]
	},
	setValue: {
		onSuccess: () => raiseToast(__('Account settings saved successfully')),
	},
	onSuccess: (data: MailAccount) => (setCustomReplyTo.value = !!data.reply_to),
})

const setCustomReplyTo = ref(account.doc?.reply_to)

const userAddresses = createResource({ url: 'mail.api.mail.get_user_addresses', auto: true })
</script>

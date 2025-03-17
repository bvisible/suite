<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('New Group'),
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					disabled: !(group.doc.username && group.doc.domain_name),
					onClick: group.submit,
				},
			],
		}"
	>
		<template #body-content>
			<div class="mb-4 flex items-center justify-between">
				<FormControl
					v-model="group.doc.username"
					type="text"
					:label="__('Username')"
					placeholder="team"
					class="w-full"
				/>
				<FeatherIcon class="mx-2.5 mb-1.5 mt-auto h-4 w-4 text-gray-400" name="at-sign" />
				<LinkControl
					v-model="group.doc.domain_name"
					:label="__('Domain Name')"
					placeholder="yourdomain.com"
					doctype="Mail Domain"
					:filters="{ tenant: user.data.tenant, is_verified: 1 }"
					class="w-full"
				/>
			</div>
			<FormControl
				v-model="group.doc.display_name"
				type="text"
				:label="__('Display Name')"
				placeholder="Team Example"
			/>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Dialog, FeatherIcon, FormControl } from 'frappe-ui'
import { useNewDoc } from 'frappe-ui/src/data-fetching'

import { raiseToast } from '@/utils'
import LinkControl from '@/components/Controls/LinkControl.vue'

const show = defineModel<boolean>()

const emit = defineEmits(['reload-groups'])

const user = inject('$user')
const router = useRouter()

const defaultGroup = {
	username: '',
	domain_name: '',
	display_name: '',
}

const group = useNewDoc(
	'Mail Group',
	{ ...defaultGroup },
	{
		beforeSubmit: () => {
			group.doc.email = `${group.doc.username}@${group.doc.domain_name}`
		},
		onSuccess: () => {
			show.value = false
			raiseToast(__('Group created successfully'))
			router.push({ name: 'Group', params: { groupName: group.doc.email } })
		},
		onError: (error) => raiseToast(error.message, 'error'),
	},
)

watch(show, (val) => {
	if (val) Object.assign(group.doc, defaultGroup)
})
</script>

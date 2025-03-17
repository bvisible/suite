<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('New Alias'),
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					disabled: !Object.values(alias.doc).every(Boolean),
					onClick: alias.submit,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<div class="flex items-center justify-between">
					<FormControl
						v-model="alias.doc.username"
						type="text"
						:label="__('Username')"
						placeholder="johndoe"
						class="w-full"
					/>
					<FeatherIcon
						class="mx-2.5 mb-1.5 mt-auto h-4 w-4 text-gray-400"
						name="at-sign"
					/>
					<LinkControl
						v-model="alias.doc.domain_name"
						:label="__('Domain Name')"
						placeholder="yourdomain.com"
						doctype="Mail Domain"
						:filters="{ tenant: user.data.tenant, is_verified: 1 }"
						class="w-full"
					/>
				</div>
				<FormControl
					v-model="alias.doc.alias_for_type"
					type="select"
					:label="__('Alias For')"
					:options="[
						{ label: __('Mail Account'), value: 'Mail Account' },
						{ label: __('Mail Group'), value: 'Mail Group' },
					]"
				/>
				<LinkControl
					v-model="alias.doc.alias_for_name"
					:label="
						__(
							alias.doc.alias_for_type === 'Mail Account'
								? 'Mail Account'
								: 'Mail Group',
						)
					"
					:doctype="
						alias.doc.alias_for_type === 'Mail Account' ? 'Mail Account' : 'Mail Group'
					"
					:filters="{ tenant: user.data.tenant, enabled: 1 }"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { inject, watch } from 'vue'
import { Dialog, FeatherIcon, FormControl } from 'frappe-ui'
import { useNewDoc } from 'frappe-ui/src/data-fetching'

import { raiseToast } from '@/utils'
import LinkControl from '@/components/Controls/LinkControl.vue'

const show = defineModel<boolean>()

const emit = defineEmits(['reload-aliases'])

const user = inject('$user')

const defaultAlias = {
	username: '',
	domain_name: '',
	alias_for_type: 'Mail Account',
	alias_for_name: '',
}

const alias = useNewDoc(
	'Mail Alias',
	{ ...defaultAlias },
	{
		beforeSubmit: () => {
			alias.doc.email = `${alias.doc.username}@${alias.doc.domain_name}`
		},
		onSuccess: () => {
			show.value = false
			raiseToast(__('Alias created successfully'))
			emit('reload-aliases')
		},
		onError: (error) => raiseToast(error.message, 'error'),
	},
)

watch(show, (val) => {
	if (val) Object.assign(alias.doc, defaultAlias)
})

watch(
	() => alias.doc.alias_for_type,
	() => {
		alias.doc.alias_for_name = ''
	},
)
</script>

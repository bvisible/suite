<template>
	<div class="mb-4 flex items-center">
		<h1 class="font-semibold">API Access</h1>
		<Button
			:label="__(user.data?.api_key ? 'Regenerate Secret' : 'Generate Keys')"
			class="ml-auto"
			@click="generateKeys.submit()"
		/>
	</div>

	<CopyControl v-if="user.data?.api_key" :label="__('API Key')" :value="user.data?.api_key" />

	<div v-else class="mt-2">
		<p class="text-base">
			{{ __(`You don't have an API key yet. Generate one to access the API.`) }}
		</p>
	</div>

	<Dialog v-model="showSecret" :options="{ title: __('API Access') }">
		<template #body-content>
			<p class="text-base">
				{{ __(`Please copy the API secret now. You won’t be able to see it again!`) }}
			</p>
			<CopyControl :label="__('API Key')" :value="user.data?.api_key" />
			<CopyControl :label="__('API Secret')" :value="apiSecret" />
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { inject, ref } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'

import CopyControl from '@/components/Controls/CopyControl.vue'

const user = inject('$user')
const showSecret = ref(false)
const apiSecret = ref('')

const generateKeys = createResource({
	url: 'frappe.core.doctype.user.user.generate_keys',
	makeParams() {
		return {
			user: user.data?.name,
		}
	},
	onSuccess(data) {
		if (!user.data?.api_key) user.reload()
		apiSecret.value = data.api_secret
		showSecret.value = true
	},
})
</script>

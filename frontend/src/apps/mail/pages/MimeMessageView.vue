<template>
	<div class="mx-auto space-y-8 rounded-md border bg-white p-12 sm:w-[75rem]">
		<template v-if="mime.data">
			<div class="flex items-center justify-between">
				<h1 class="text-xl !font-medium">{{ __('MIME Message') }}</h1>
				<Button
					:label="__('Copy to Clipboard')"
					size="md"
					@click="copyToClipBoard(message)"
				/>
			</div>
			<div class="rounded-md border">
				<div class="border-b px-6 py-4">
					<h2>{{ __('Message Information') }}</h2>
				</div>
				<div
					v-for="[key, value] of Object.entries(mime.data)"
					:key="key"
					class="flex items-center px-6 py-4 text-base last:rounded-b even:bg-gray-50/70"
				>
					<div class="w-1/4 text-gray-600">{{ value.label }}</div>
					<div class="flex w-3/4 items-center">{{ value.value }}</div>
				</div>
			</div>
			<pre class="text-wrap break-words" style="font-size: 0.875rem">{{ message }}</pre>
		</template>

		<div v-else-if="mime.error" class="space-y-4 text-center">
			<h1 class="text-xl !font-medium text-red-500">{{ __('Error') }}</h1>
			<div class="text-gray-600" v-html="mime.error.messages[0]" />
			<Button :label="__('Return to Home')" size="md" @click="$router.push('/')" />
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Button, createResource } from 'frappe-ui'

import { copyToClipBoard } from '@/utils'

const route = useRoute()
const message = ref('')

interface MimeField {
	label: string
	value: string
}

interface Mime {
	message?: string
	message_id: MimeField
	created_at: MimeField
	subject: MimeField
	from: MimeField
	to: MimeField
	cc?: MimeField
	bcc?: MimeField
	spf?: MimeField
	dkim?: MimeField
	dmarc?: MimeField
}

const mime = createResource({
	url: 'mail.api.mail.get_mime_message',
	auto: true,
	makeParams: () => ({ name: route.params.id }),
	transform: (data: Mime) => {
		message.value = data.message as string
		delete data.message
		if (data.cc && !data.cc.value) delete data.cc
		if (data.bcc && !data.bcc.value) delete data.bcc
	},
})
</script>

<template>
	<div v-if="mailDataExchange.data" class="flex h-screen flex-col">
		<header class="flex items-center border-b px-5 py-2.5">
			<Breadcrumbs :items="BREADCRUMBS" />
		</header>
		<div class="mx-auto my-5 rounded border p-12 sm:w-[60rem]">
			<div class="mb-4 flex items-center space-x-2">
				<h1 class="text-xl !font-semibold">{{ __('Mail Data Exchange') }}</h1>
				<Badge
					:theme="getTheme(mailDataExchange.data?.status)"
					:label="mailDataExchange.data?.status"
				/>
			</div>
			<p class="text-base">
				{{
					__('{0} · Started at {1} · Completed at {2}', [
						mailDataExchange.data?.operation,
						dayjs(mailDataExchange.data?.started_at).format('MMM D, YYYY h:mm A'),
						dayjs(mailDataExchange.data?.completed_at).format('MMM D, YYYY h:mm A'),
					])
				}}
			</p>
			<hr class="my-8" />
			<h2 class="mb-4">{{ __('Output') }}</h2>
			<CopyCode :code="mailDataExchange.data?.output" class="max-h-80 overflow-y-auto" />
			<template v-if="attachment.data?.file_url">
				<hr class="my-8" />
				<h2 class="mb-4">{{ __('File') }}</h2>
				<div class="flex items-center justify-between">
					<p class="text-base">
						{{
							__('{0} · {1}', [
								attachment.data?.file_type,
								formatBytes(attachment.data?.file_size),
							])
						}}
					</p>
					<Button
						icon-left="download"
						:label="__('Download')"
						@click="triggerDownload"
					/>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { Badge, Breadcrumbs, Button, createResource } from 'frappe-ui'

import { formatBytes, getTheme } from '@/utils'
import CopyCode from '@/components/CopyCode.vue'

const { id } = defineProps<{ id: string }>()

const dayjs = inject('$dayjs')

const mailDataExchange = createResource({
	url: 'frappe.client.get_value',
	makeParams: () => ({
		doctype: 'Mail Data Exchange',
		filters: { name: id },
		fieldname: ['status', 'operation', 'started_at', 'completed_at', 'output'],
	}),
	auto: true,
})

const attachment = createResource({
	url: 'frappe.client.get_value',
	makeParams: () => ({
		doctype: 'File',
		fieldname: ['file_size', 'file_url', 'file_type', 'file_name'],
		filters: {
			attached_to_doctype: 'Mail Data Exchange',
			attached_to_name: id,
			attached_to_field: 'file',
		},
	}),
	auto: true,
})

const triggerDownload = () => {
	const link = document.createElement('a')
	link.href = attachment.data?.file_url
	link.download = attachment.data?.file_name
	document.body.appendChild(link)
	link.click()
	document.body.removeChild(link)
}

const BREADCRUMBS = [
	{ label: __('Mail Data Exchanges'), route: '/mail-data-exchanges' },
	{ label: id },
]
</script>

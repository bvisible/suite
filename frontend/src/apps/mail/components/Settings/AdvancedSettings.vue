<template>
	<h1>{{ __('Mail Data Exchange') }}</h1>
	<FormControl
		v-model="mailDataExchange.operation"
		:label="__('Operation')"
		type="select"
		:options="['Import', 'Export']"
	/>

	<template v-if="mailDataExchange.operation === 'Import'">
		<FormControl
			v-model="mailDataExchange.import_format"
			:label="__('Format')"
			type="select"
			:options="['jmap', 'mbox', 'maildir', 'maildir-nested']"
		/>
		<FileUploader
			:file-types="['.zip', '.tgz', '.tar.gz']"
			:upload-args="{ private: true }"
			@success="(file) => (mailDataExchange.import_file = file.file_url)"
		>
			<template #default="{ openFileSelector }">
				<Button class="w-full" :label="__('Upload File')" @click="openFileSelector" />
				<p v-if="mailDataExchange.import_file" class="mt-2 text-sm">
					{{ __('File uploaded: {0}', [mailDataExchange.import_file]) }}
				</p>
			</template>
		</FileUploader>
	</template>

	<FormControl
		v-else
		v-model="mailDataExchange.export_archive_type"
		:label="__('Archive Type')"
		type="select"
		:options="['.zip', '.tgz', '.tar.gz']"
	/>

	<Button
		class="min-h-7"
		:label="
			mailDataExchange.operation === 'Import' ? __('Create Import') : __('Create Export')
		"
		:disabled="
			!!noOfActiveOperations ||
			(mailDataExchange.operation === 'Import' && !mailDataExchange.import_file)
		"
		@click="createMailDataExchange.submit()"
	/>
	<div v-if="noOfActiveOperations" class="text-ink-gray-5 flex items-center space-x-1.5">
		<LoaderCircle class="h-4 w-4 animate-spin" />
		<span class="text-sm"> {{ activeOperationMessage }} </span>
	</div>
	<ErrorMessage
		v-if="createMailDataExchange.error"
		:message="createMailDataExchange.error"
		class="mb-2.5"
	/>

	<h1>{{ __('API Access') }}</h1>
	<CopyControl v-if="user.data?.api_key" :label="__('API Key')" :value="user.data?.api_key" />
	<p v-else class="text-base">
		{{ __(`You don't have an API key yet. Generate one to access the API.`) }}
	</p>
	<Button
		class="min-h-7"
		:label="user.data?.api_key ? __('Regenerate Secret') : __('Generate Keys')"
		@click="generateKeys.submit()"
	/>

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
import { computed, inject, reactive, ref } from 'vue'
import { LoaderCircle } from 'lucide-vue-next'
import { Button, Dialog, ErrorMessage, FileUploader, FormControl, createResource } from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'

import CopyControl from '@/components/Controls/CopyControl.vue'

const user = inject('$user')

// Mail Data Exchange

const mailDataExchange = reactive({
	operation: 'Import',
	import_format: 'jmap',
	import_file: '',
	export_archive_type: '.zip',
})

const createMailDataExchange = createResource({
	url: 'mail.api.account.create_mail_data_exchange',
	makeParams: () => mailDataExchange,
	onSuccess: () => activeOperations.reload(),
})

const activeOperations = useList({
	doctype: 'Mail Data Exchange',
	immediate: true,
	fields: ['name', 'operation'],
	filters: { account: user.data.name, status: ['in', ['Queued', 'In Progress']] },
})

const noOfActiveOperations = computed(
	() =>
		activeOperations.data?.filter((d) => d.operation === mailDataExchange.operation)?.length ||
		0,
)

const activeOperationMessage = computed(() =>
	__('Your mail data {0} is in progress. You’ll receive an email once it’s complete.', [
		mailDataExchange.operation === 'Import' ? __('import') : __('export'),
	]),
)

// API Access

const showSecret = ref(false)
const apiSecret = ref('')

const generateKeys = createResource({
	url: 'frappe.core.doctype.user.user.generate_keys',
	makeParams: () => ({ user: user.data?.name }),
	onSuccess: (data) => {
		if (!user.data?.api_key) user.reload()
		apiSecret.value = data.api_secret
		showSecret.value = true
	},
})
</script>

<template>
	<div v-if="domain?.doc" class="flex h-full flex-col">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="BREADCRUMBS" />
			<div class="flex space-x-2">
				<Dropdown :options="dropdownOptions" :button="{ icon: 'more-horizontal' }" />
				<Button
					v-if="!domain.doc.is_verified"
					variant="solid"
					:label="__(domain.doc.enabled ? 'Verify DNS Records' : 'Enable')"
					@click="
						domain.doc.enabled
							? domain.verifyDnsRecords.submit()
							: domain.setValue.submit({ enabled: 1 })
					"
				/>
			</div>
		</header>
		<div class="m-6">
			<ListView
				class="flex-1"
				:columns="LIST_COLUMNS"
				:rows="domain.doc.dns_records"
				:options="{ selectable: false }"
				row-key="name"
			>
				<ListHeader />
				<ListRows>
					<ListRow v-for="row in domain.doc.dns_records" :key="row.name" :row="row">
						<template #default="{ item }">
							<ListRowItem>
								<div class="cursor-copy" @click="copyToClipBoard(item)">
									{{ item }}
								</div>
							</ListRowItem>
						</template>
					</ListRow>
				</ListRows>
			</ListView>
		</div>
	</div>
	<Dialog v-model="showConfirmDialog" :options="confirmDialogOptions" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
	Badge,
	Breadcrumbs,
	Button,
	Dialog,
	Dropdown,
	ListHeader,
	ListRow,
	ListRowItem,
	ListRows,
	ListView,
	createDocumentResource,
} from 'frappe-ui'

import { copyToClipBoard, raiseToast } from '@/utils'

const props = defineProps<{ domainName: string }>()

const router = useRouter()

const showConfirmDialog = ref(false)

const domain = createDocumentResource({
	doctype: 'Mail Domain',
	name: props.domainName,
	setValue: {
		onSuccess: () => {
			showConfirmDialog.value = false
			raiseToast(__('Domain settings updated.'))
		},
		onError: (error) => {
			raiseToast(error.messages[0], 'error')
			domain.reload()
		},
	},
	whitelistedMethods: {
		verifyDnsRecords: {
			method: 'verify_dns_records',
			makeParams: () => ({ do_not_save: false }),
			onSuccess: (data) => {
				raiseToast(
					data ? 'DNS records verified successfully.' : 'DNS verification failed.',
					data ? 'success' : 'error',
				)
				domain.reload()
			},
			onError: (error) => {
				raiseToast(error.messages[0], 'error')
				domain.reload()
			},
		},
		refreshDnsRecords: {
			method: 'refresh_dns_records',
			makeParams: () => ({ do_not_save: false }),
			onSuccess: () => {
				showConfirmDialog.value = false
				raiseToast('DNS Records refreshed successfully.')
				domain.reload()
			},
			onError: (error) => {
				raiseToast(error.messages[0], 'error')
				domain.reload()
			},
		},
		rotateDkimKeys: {
			method: 'rotate_dkim_keys',
			onSuccess: () => {
				showConfirmDialog.value = false
				raiseToast('DKIM Keys rotated successfully.')
				domain.reload()
			},
			onError: (error) => {
				raiseToast(error.messages[0], 'error')
				domain.reload()
			},
		},
	},
	onError: () => router.replace({ name: 'Domains' }),
})

const BREADCRUMBS = [
	{ label: __('Domains'), route: '/dashboard/domains' },
	{ label: props.domainName },
]

const confirmDialogAction = ref<'refreshDnsRecords' | 'rotateDkimKeys' | 'disableDomain'>(
	'refreshDnsRecords',
)

const confirmDialogOptions = computed(() => {
	const config = {
		refreshDnsRecords: {
			title: __('Refresh DNS Records'),
			message: __(
				`Are you sure you want to refresh the DNS records? If there are any changes, you'll need to update the DNS settings with your DNS provider accordingly.`,
			),
			action: domain.refreshDnsRecords.submit,
		},
		rotateDkimKeys: {
			title: __('Rotate DKIM Keys'),
			message: __(
				`Are you sure you want to rotate the DKIM keys? This will generate new keys for email signing and may take up to 10 minutes to propagate across DNS servers. Emails sent during this period may fail DKIM verification.`,
			),
			action: domain.rotateDkimKeys.submit,
		},
		disableDomain: {
			title: __('Disable Domain'),
			message: __(
				`Are you sure you want to disable this domain? Email services for this domain will stop working immediately.`,
			),
			action: () => domain.setValue.submit({ enabled: 0 }),
		},
	}[confirmDialogAction.value]

	return {
		title: config.title,
		message: config.message,
		size: 'xl',
		icon: { name: 'alert-triangle', appearance: 'warning' },
		actions: [{ label: __('Confirm'), variant: 'solid', onClick: config.action }],
	}
})

const dropdownOptions = computed(() => [
	{
		label: __('Disable Domain'),
		icon: 'eye-off',
		onClick: () => {
			confirmDialogAction.value = 'disableDomain'
			showConfirmDialog.value = true
		},
		condition: () => domain.doc.enabled,
	},
	{
		label: __('Refresh DNS Records'),
		icon: 'refresh-cw',
		onClick: () => {
			confirmDialogAction.value = 'refreshDnsRecords'
			showConfirmDialog.value = true
		},
	},
	{
		label: __('Rotate DKIM Keys'),
		icon: 'rotate-cw',
		onClick: () => {
			confirmDialogAction.value = 'rotateDkimKeys'
			showConfirmDialog.value = true
		},
	},
	{
		label: __('View in Desk'),
		icon: 'external-link',
		onClick: () => window.open(`/app/mail-domain/${props.domainName}`, '_blank')?.focus(),
	},
])

const LIST_COLUMNS = [
	{ label: 'Type', key: 'type', width: '10%' },
	{ label: 'Host', key: 'host', width: '20%' },
	{ label: 'Priority', key: 'priority', width: '10%' },
	{ label: 'Value', key: 'value', width: '50%' },
	{ label: 'TTL (Recommended)', key: 'ttl', width: '10%' },
]
</script>

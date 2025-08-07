<template>
	<div class="flex h-screen flex-col">
		<header class="flex items-center border-b px-5 py-2.5">
			<h1>{{ __('Mail Transfers') }}</h1>
		</header>
		<div class="m-5 flex flex-1 flex-col space-y-5 overflow-y-auto">
			<div class="flex items-center space-x-3">
				<FormControl
					v-model="operation"
					:label="__('Operation')"
					type="select"
					:options="OPERATION_OPTIONS"
					class="w-40"
				/>
				<FormControl
					v-model="status"
					:label="__('Status')"
					type="select"
					:options="STATUS_OPTIONS"
					class="w-40"
				/>
			</div>
			<ListView
				v-if="mailTransfers.data"
				:columns="listColumns"
				:rows="mailTransfers.data"
				:options="LIST_OPTIONS"
				row-key="name"
				class="flex-1"
			>
				<ListHeader />
				<ListRows>
					<template v-if="mailTransfers.data.length">
						<ListRow
							v-for="row in mailTransfers.data"
							:key="row.name"
							v-slot="{ item, column }"
							:row="row"
						>
							<ListRowItem :item="item">
								<Badge
									v-if="column.key == 'status'"
									:theme="getTheme(item)"
									:label="item"
								/>
							</ListRowItem>
						</ListRow>
					</template>
					<ListEmptyState v-else />
				</ListRows>
			</ListView>
			<ErrorMessage v-if="mailTransfers.error" :message="mailTransfers.error" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import {
	Badge,
	ErrorMessage,
	FormControl,
	ListEmptyState,
	ListHeader,
	ListRow,
	ListRowItem,
	ListRows,
	ListView,
} from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'

const user = inject('$user')
const dayjs = inject('$dayjs')

const operation = ref('Import')
const status = ref('')

const OPERATION_OPTIONS = [
	{ label: __('Import'), value: 'Import' },
	{ label: __('Export'), value: 'Export' },
]

const STATUS_OPTIONS = [
	{ label: '', value: '' },
	{ label: __('Draft'), value: 'Draft' },
	{ label: __('Queued'), value: 'Queued' },
	{ label: __('In Progress'), value: 'In Progress' },
	{ label: __('Completed'), value: 'Completed' },
	{ label: __('Failed'), value: 'Failed' },
	{ label: __('Cancelled'), value: 'Cancelled' },
]

const mailTransfers = useList({
	doctype: 'Mail Data Exchange',
	fields: [
		'name',
		'status',
		'import_format',
		'export_archive_type',
		'import_file',
		'started_at',
		'completed_at',
	],
	filters: () => {
		const filters: Record<string, string> = {
			account: user.data.name,
			operation: operation.value,
		}
		if (status.value) filters.status = status.value
		return filters
	},
	orderBy: 'creation desc',
	transform: (data) =>
		data.map((row) => ({
			...row,
			started_at: dayjs(row.started_at).format('MMM D, YYYY h:mm A'),
			completed_at: dayjs(row.completed_at).format('MMM D, YYYY h:mm A'),
		})),
})

const listColumns = computed(() => {
	const columns = []
	if (operation.value === 'Import')
		columns.push(
			{ label: __('Format'), key: 'import_format' },
			{ label: __('File'), key: 'import_file' },
		)
	else columns.push({ label: __('Archive Type'), key: 'export_archive_type' })
	columns.push(
		{ label: __('Started At'), key: 'started_at' },
		{ label: __('Completed At'), key: 'completed_at' },
		{ label: __('Status'), key: 'status' },
	)
	return columns
})

const LIST_OPTIONS = {
	selectable: false,
	emptyState: { description: __('No mail transfers found.') },
}

const getTheme = (
	status: 'Draft' | 'Queued' | 'In Progress' | 'Completed' | 'Failed' | 'Cancelled',
) => {
	switch (status) {
		case 'Draft':
			return 'gray'
		case 'Completed':
			return 'green'
		case 'Failed':
		case 'Cancelled':
			return 'red'
		default:
			return 'blue'
	}
}
</script>

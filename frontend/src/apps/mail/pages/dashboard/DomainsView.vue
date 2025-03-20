<template>
	<DashboardLayout
		:breadcrumbs="[{ label: __('Domains') }]"
		:button-label="__('Add Domain')"
		:button-action="() => (showAddDomain = true)"
	>
		<div class="flex items-center space-x-3">
			<FormControl v-model="search" :placeholder="__('Search')" class="w-80">
				<template #prefix>
					<FeatherIcon name="search" class="w-4 text-gray-600" />
				</template>
			</FormControl>
			<FormControl
				v-model="status"
				:placeholder="__('Status')"
				class="w-40"
				type="select"
				:options="STATUS_OPTIONS"
			/>
		</div>
		<ListView
			v-if="domains?.data"
			class="flex-1"
			:columns="LIST_COLUMNS"
			:rows="domains.data"
			:options="LIST_OPTIONS"
			row-key="name"
		>
			<ListHeader />
			<ListRows>
				<template v-if="domains.data.length">
					<ListRow
						v-for="row in domains.data"
						:key="row.name"
						v-slot="{ column, item }"
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
	</DashboardLayout>
	<AddDomainModal v-model="showAddDomain" @reload-domains="domains.reload()" />
</template>
<script setup lang="ts">
import { inject, ref } from 'vue'
import { useDebounce } from '@vueuse/core'
import {
	Badge,
	FeatherIcon,
	FormControl,
	ListEmptyState,
	ListHeader,
	ListRow,
	ListRowItem,
	ListRows,
	ListView,
} from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'

import DashboardLayout from '@/components/DashboardLayout.vue'
import AddDomainModal from '@/components/Modals/AddDomainModal.vue'

const user = inject('$user')

const showAddDomain = ref(false)
const search = ref('')
const debouncedSearch = useDebounce(search, 500)
const status = ref<'Verified' | 'Not Verified' | 'Disabled' | ''>('')

const domains = useList({
	doctype: 'Mail Domain',
	fields: ['name', 'enabled', 'is_verified'],
	filters: () => {
		const filters: Record<string, string | string[] | number> = {
			tenant: user.data?.tenant,
			name: ['like', debouncedSearch.value],
		}
		if (status.value) {
			filters.is_verified = status.value === 'Verified' ? 1 : 0
			filters.enabled = status.value === 'Disabled' ? 0 : 1
		}
		return filters
	},
	limit: 100,
	transform: (data) =>
		data.map((row) => ({
			...row,
			status: row.is_verified ? 'Verified' : row.enabled ? 'Not Verified' : 'Disabled',
		})),
	cacheKey: ['mailTenantDomains', user.data?.tenant, debouncedSearch.value, status.value],
})

const getTheme = (status: 'Verified' | 'Not Verified' | 'Disabled') =>
	status === 'Verified' ? 'green' : status === 'Not Verified' ? 'orange' : 'gray'

const LIST_COLUMNS = [
	{ label: __('Domain'), key: 'name' },
	{ label: __('Status'), key: 'status' },
]

const LIST_OPTIONS = {
	selectable: false,
	showTooltip: false,
	emptyState: { description: __('No domains configured') },
	getRowRoute: (row) => ({ name: 'Domain', params: { domainName: row.name } }),
}

const STATUS_OPTIONS = [
	{ label: '', value: '' },
	{ label: __('Verified'), value: 'Verified' },
	{ label: __('Not Verified'), value: 'Not Verified' },
	{ label: __('Disabled'), value: 'Disabled' },
]
</script>

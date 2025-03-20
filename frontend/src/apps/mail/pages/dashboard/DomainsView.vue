<template>
	<div class="flex h-full flex-col">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="[{ label: __('Domains') }]" />
			<Button :label="__('Add Domain')" icon-left="plus" @click="showAddDomain = true" />
		</header>
		<div class="m-5 flex flex-1 flex-col">
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
		</div>
	</div>
	<AddDomainModal v-model="showAddDomain" @reload-domains="domains.reload()" />
</template>
<script setup lang="ts">
import { inject, ref } from 'vue'
import {
	Badge,
	Breadcrumbs,
	Button,
	ListEmptyState,
	ListHeader,
	ListRow,
	ListRowItem,
	ListRows,
	ListView,
} from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'

import AddDomainModal from '@/components/Modals/AddDomainModal.vue'

const user = inject('$user')

const showAddDomain = ref(false)

const LIST_COLUMNS = [
	{
		label: __('Domain'),
		key: 'name',
	},
	{
		label: __('Status'),
		key: 'status',
	},
]

const LIST_OPTIONS = {
	selectable: false,
	showTooltip: false,
	emptyState: { description: __('No domains configured') },
	getRowRoute: (row) => ({ name: 'Domain', params: { domainName: row.name } }),
}

const domains = useList({
	doctype: 'Mail Domain',
	fields: ['name', 'enabled', 'is_verified'],
	filters: { tenant: user.data?.tenant },
	limit: 100,
	cacheKey: ['mailTenantDomains', user.data?.tenant],
	transform: (data) =>
		data.map((row) => ({
			...row,
			status: row.is_verified ? 'Verified' : row.enabled ? 'Not Verified' : 'Disabled',
		})),
})

const getTheme = (status: 'Verified' | 'Not Verified' | 'Disabled') =>
	status === 'Verified' ? 'green' : status === 'Not Verified' ? 'orange' : 'gray'
</script>

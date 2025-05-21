<template>
	<div
		class="flex h-full flex-col justify-between border-r bg-gray-50 transition-all duration-300 ease-in-out"
		:class="isSidebarCollapsed ? 'w-14' : 'w-56'"
	>
		<div
			class="flex flex-col overflow-hidden"
			:class="isSidebarCollapsed ? 'items-center' : ''"
		>
			<UserDropdown class="p-2" :is-collapsed="isSidebarCollapsed" />
			<div class="flex flex-col overflow-y-auto">
				<SidebarLink
					v-for="link in sidebarLinks"
					:key="link.label"
					:link="link"
					:is-collapsed="isSidebarCollapsed"
					class="mx-2 my-0.5"
				/>
			</div>
		</div>
		<SidebarLink
			:link="{
				label: isSidebarCollapsed ? 'Expand' : 'Collapse',
			}"
			:is-collapsed="isSidebarCollapsed"
			class="m-2"
			@click="isSidebarCollapsed = !isSidebarCollapsed"
		>
			<template #icon>
				<span class="grid h-5 w-6 flex-shrink-0 place-items-center">
					<ArrowLeftFromLine
						class="h-4 w-4 text-gray-700 duration-300 ease-in-out"
						:class="{
							'[transform:rotateY(180deg)]': isSidebarCollapsed,
						}"
					/>
				</span>
			</template>
		</SidebarLink>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useStorage } from '@vueuse/core'
import { ArrowLeftFromLine } from 'lucide-vue-next'
import { createResource } from 'frappe-ui'

import SidebarLink from '@/components/SidebarLink.vue'
import UserDropdown from '@/components/UserDropdown.vue'

const sidebarItems = ref([
	{
		label: __('Domains'),
		icon: 'Globe',
		to: 'Domains',
		activeFor: ['Domains', 'Domain'],
		forDashboard: true,
	},
	{
		label: __('Members'),
		icon: 'Users',
		to: 'Members',
		activeFor: ['Members', 'Invites'],
		forDashboard: true,
	},
	{
		label: __('Groups'),
		icon: 'Mails',
		to: 'Groups',
		activeFor: ['Groups', 'Group'],
		forDashboard: true,
	},
	{
		label: __('Aliases'),
		icon: 'AtSign',
		to: 'Aliases',
		activeFor: ['Aliases'],
		forDashboard: true,
	},
])

const route = useRoute()

const sidebarLinks = computed(() =>
	sidebarItems.value.filter((link) =>
		route.meta.isDashboard ? link.forDashboard : !link.forDashboard,
	),
)

createResource({
	url: 'mail.api.mail.get_user_mailboxes',
	auto: true,
	onSuccess: (data) =>
		data.forEach((mailbox) => {
			sidebarItems.value.push({
				label: mailbox.name,
				icon: MAILBOX_ICONS[mailbox.role],
				to: { name: 'Mailbox', params: { id: mailbox.role } },
				activeFor: ['Mailbox'],
			})
		})!,
})

const MAILBOX_ICONS = {
	inbox: 'Inbox',
	sent: 'Send',
	trash: 'Trash2',
	junk: 'MailWarning',
	drafts: 'Edit3',
}

const getSidebarFromStorage = () => useStorage('sidebar_is_collapsed', false)

const isSidebarCollapsed = ref(getSidebarFromStorage())
</script>

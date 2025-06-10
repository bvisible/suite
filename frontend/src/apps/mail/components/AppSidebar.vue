<template>
	<div
		v-if="isMobile && isSidebarOpen"
		class="fixed inset-0 z-40 bg-black bg-opacity-50"
		@click="closeSidebar"
	/>

	<div
		v-if="!isMobile || isSidebarOpen"
		class="flex h-full flex-col justify-between border-r bg-gray-50 transition-all duration-300 ease-in-out"
		:class="[
			isSidebarCollapsed && !isMobile ? 'w-14' : 'w-56',
			isMobile ? 'fixed left-0 top-0 z-50 shadow-lg' : 'relative',
		]"
	>
		<div
			class="flex flex-col overflow-hidden"
			:class="{ 'items-center': isSidebarCollapsed && !isMobile }"
		>
			<UserDropdown class="p-2" :is-collapsed="isSidebarCollapsed && !isMobile" />
			<div class="flex flex-col">
				<SidebarLink
					v-for="link in sidebarLinks"
					:key="link.label"
					:link="link"
					:is-collapsed="isSidebarCollapsed && !isMobile"
					class="mx-2 my-0.5"
				/>
			</div>
		</div>
		<SidebarLink
			v-if="!isMobile"
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

import { useScreenSize, useSidebar } from '@/utils/composables'
import SidebarLink from '@/components/SidebarLink.vue'
import UserDropdown from '@/components/UserDropdown.vue'

const { isMobile } = useScreenSize()
const { isSidebarOpen, closeSidebar } = useSidebar()
const getSidebarFromStorage = () => useStorage('sidebar_is_collapsed', false)
const isSidebarCollapsed = ref(getSidebarFromStorage())

interface SidebarItem {
	label: string
	icon: string
	to: { name: string; params?: Record<string, string> }
	activeFor: string[]
	forDashboard?: boolean
}

const sidebarItems = ref<SidebarItem[]>([
	{
		label: __('Domains'),
		icon: 'Globe',
		to: { name: 'Domains' },
		activeFor: ['Domains', 'Domain'],
		forDashboard: true,
	},
	{
		label: __('Members'),
		icon: 'Users',
		to: { name: 'Members' },
		activeFor: ['Members', 'Invites'],
		forDashboard: true,
	},
	{
		label: __('Mailing Lists'),
		icon: 'Mails',
		to: { name: 'MailingLists' },
		activeFor: ['MailingLists', 'MailingList'],
		forDashboard: true,
	},
	{
		label: __('Aliases'),
		icon: 'AtSign',
		to: { name: 'Aliases' },
		activeFor: ['Aliases'],
		forDashboard: true,
	},
])

const route = useRoute()

const sidebarLinks = computed(() =>
	sidebarItems.value.filter((link) => route.meta.isDashboard == link.forDashboard),
)

createResource({
	url: 'mail.api.mail.get_mailboxes',
	auto: true,
	onSuccess: (data: { name: string; role: string }[]) =>
		data.forEach((mailbox) => {
			sidebarItems.value.push({
				label: mailbox.name,
				icon: MAILBOX_ICONS[mailbox.role],
				to: { name: 'Mailbox', params: { mailbox: mailbox.role } },
				activeFor: [mailbox.role],
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
</script>

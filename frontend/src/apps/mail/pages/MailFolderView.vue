<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="[{ label: currentFolder }]">
			<template #suffix>
				<div class="ml-2 self-end text-xs text-gray-600">
					{{
						__('{0} {1}', [
							formatNumber(mailCount?.data || 0),
							mailCount?.data == 1 ? singularize('messages') : 'messages',
						])
					}}
				</div>
			</template>
		</Breadcrumbs>
		<HeaderActions @reload-mails="reloadMails('Drafts')" />
	</header>
	<div v-if="mails[currentFolder].data" class="flex h-[calc(100vh-3.2rem)]">
		<div
			ref="mailSidebar"
			class="sticky top-16 w-1/3 overflow-y-scroll overscroll-contain border-r p-3"
			@scroll="loadMoreEmails"
		>
			<div
				v-for="(mail, idx) in mails[currentFolder].data"
				:key="idx"
				class="flex cursor-pointer flex-col space-y-1 rounded"
				:class="{ 'bg-gray-100': mail.name == currentMail[currentFolder] }"
				@click="openMail(mail)"
			>
				<SidebarDetail :mail="mail" />
				<div
					:class="{
						'mx-4 h-[0.25px] border-b border-gray-100':
							idx < mails[currentFolder].data.length - 1,
					}"
				/>
			</div>
		</div>
		<div class="flex w-px cursor-col-resize justify-center" @mousedown="startResizing">
			<div
				ref="resizer"
				class="h-full w-[2px] rounded-full transition-all duration-300 ease-in-out group-hover:bg-gray-400"
			/>
		</div>
		<div class="w-2/3 flex-1 overflow-auto">
			<MailDetails
				ref="mailDetails"
				:mail-i-d="currentMail[currentFolder]"
				:type="doctype"
				@reload-mails="reloadMails"
				@mark-as-unread="setSeen.submit({ name: currentMail[currentFolder], seen: 0 })"
			/>
		</div>
	</div>
</template>
<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { Breadcrumbs, createListResource, createResource } from 'frappe-ui'

import { formatNumber, singularize, startResizing } from '@/utils'
import { userStore } from '@/stores/user'
import HeaderActions from '@/components/HeaderActions.vue'
import MailDetails from '@/components/MailDetails.vue'
import SidebarDetail from '@/components/SidebarDetail.vue'

import type { Folder, UserResource } from '@/types'

const socket = inject('$socket')
const user = inject('$user') as UserResource
const { currentMail, setCurrentMail } = userStore()
const route = useRoute()

const currentFolder = computed(() => String(route.name) as Folder)
const doctype = computed(() =>
	currentFolder.value === 'Inbox' ? 'Incoming Mail' : 'Outgoing Mail',
)

const mailDetails = ref<typeof MailDetails>()

const folders: Folder[] = ['Inbox', 'Sent', 'Outbox', 'Drafts', 'Trash']

const createMailResource = (folder: Folder) =>
	createListResource({
		url: `mail.api.mail.get_${folder.toLowerCase()}_mails`,
		doctype: doctype.value,
		pageLength: 50,
		cache: [`${folder}Mails`, user.data?.name],
		onSuccess: (data) => {
			if (!data.length) return setCurrentMail(folder, null)

			if (!data.some((m) => m.name === currentMail[folder])) {
				const firstSeen = data.find((m) => m.seen)
				if (firstSeen) setCurrentMail(folder, firstSeen.name)
			}
			mailDetails.value?.reloadThread()
		},
	})

const mails = Object.fromEntries(folders.map((folder) => [folder, createMailResource(folder)]))

const mailCountFilters = computed(() =>
	currentFolder.value === 'Inbox'
		? { receiver: user.data.name }
		: { sender: user.data.name, folder: currentFolder.value },
)

const mailCount = createResource({
	url: 'frappe.client.get_count',
	auto: true,
	makeParams: () => ({
		doctype: doctype.value,
		filters: mailCountFilters.value,
	}),
	cache: [`${currentFolder.value}MailCount`, user.data?.name],
})

interface SetSeenParams {
	name: string
	seen: 1 | 0
}

const setSeen = createResource({
	url: 'mail.api.mail.set_seen',
	makeParams: (values: SetSeenParams) => ({ mail_type: doctype.value, ...values }),
	onSuccess: (data: SetSeenParams) => {
		mails[currentFolder.value].data.find((m) => m.name === data.name).seen = data.seen
		if (!data.seen) setCurrentMail(currentFolder.value, null)
	},
})

const openMail = (mail) => {
	setCurrentMail(currentFolder.value, mail.name)
	if (!mail.seen) setSeen.submit({ name: mail.name, seen: 1 })
}

const reloadMails = (folder: Folder = currentFolder.value) => {
	if (folder !== currentFolder.value) return
	mails[currentFolder.value].reload()
	mailCount.reload()
}

watch(() => currentFolder.value, reloadMails, { immediate: true })

onMounted(() => {
	socket.on('outgoing_mail_sent', () => reloadMails('Sent'))
	socket.on('incoming_mail_received', () => reloadMails('Inbox'))
})

const loadMoreEmails = useDebounceFn(() => {
	if (mails[currentFolder.value].hasNextPage) mails[currentFolder.value].next()
}, 500)
</script>

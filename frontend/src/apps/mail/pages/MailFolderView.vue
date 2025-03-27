<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="[{ label: currentFolder }]">
			<template v-if="currentFolder !== 'Trash'" #suffix>
				<div class="ml-2 self-end text-xs text-gray-600">
					{{
						__('{0} {1}', [
							formatNumber(mailCount?.data || 0),
							mailCount?.data == 1 ? 'message' : 'messages',
						])
					}}
				</div>
			</template>
		</Breadcrumbs>
		<HeaderActions :current-folder="currentFolder" @reload-mails="reloadMails" />
	</header>
	<div class="flex h-[calc(100dvh-6rem)] sm:h-[calc(100dvh-3.2rem)]">
		<template v-if="mails[currentFolder].data?.length">
			<div
				ref="mailSidebar"
				class="sticky top-16 w-full overflow-y-auto overscroll-contain border-r p-1 sm:w-1/3 sm:p-3"
				@scroll="loadMoreEmails"
			>
				<div
					v-for="(mail, idx) in mails[currentFolder].data"
					:key="idx"
					class="flex cursor-pointer flex-col space-y-1 rounded"
					:class="{ 'sm:bg-gray-100': mail.name == currentMail[currentFolder] }"
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
			<div
				class="fixed inset-0 z-20 bg-white sm:static sm:z-0 sm:w-2/3"
				:class="{
					invisible:
						screenSize.width < 640 && !(currentMail[currentFolder] || route.params.id),
				}"
			>
				<MailDetails
					ref="mailDetails"
					:mail-i-d="currentMail[currentFolder]"
					:current-folder
					:type="getMailType() || doctype"
					@reload-mails="reloadMails"
					@mark-as-unread="setSeen.submit({ name: currentMail[currentFolder], seen: 0 })"
				/>
			</div>
		</template>
		<div v-else class="flex w-full flex-col items-center justify-center space-y-3">
			<NoMailSelected class="h-16 w-16" />
			<p class="text-gray-500">
				{{ __('You have no mails in this folder.') }}
			</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { Breadcrumbs, createListResource, createResource } from 'frappe-ui'

import { formatNumber, startResizing } from '@/utils'
import { useScreenSize } from '@/utils/composables'
import { userStore } from '@/stores/user'
import HeaderActions from '@/components/HeaderActions.vue'
import NoMailSelected from '@/components/Icons/NoMailSelected.vue'
import MailDetails from '@/components/MailDetails.vue'
import SidebarDetail from '@/components/SidebarDetail.vue'

import type { Folder, UserResource } from '@/types'

const { id } = defineProps<{ id?: string }>()

const socket = inject('$socket')
const user = inject('$user') as UserResource
const { currentMail, setCurrentMail } = userStore()
const route = useRoute()
const router = useRouter()
const screenSize = useScreenSize()

const currentFolder = computed(() => {
	const name = String(route.name)
	return (name.endsWith('Mail') ? name.replace('Mail', '') : name) as Folder
})

const doctype = computed(() =>
	['Inbox', 'Spam'].includes(currentFolder.value) ? 'Incoming Mail' : 'Outgoing Mail',
)

const mailDetails = ref<typeof MailDetails>()

const folders: Folder[] = ['Inbox', 'Sent', 'Outbox', 'Drafts', 'Spam', 'Trash']

const createMailResource = (folder: Folder) =>
	createListResource({
		url: `mail.api.mail.get_${folder.toLowerCase()}_mails`,
		doctype: doctype.value,
		pageLength: 50,
		cache: [`${folder}Mails`, user.data?.name],
		onSuccess: (data) => {
			const mailExists = (id?: string | null) => id && data.some((m) => m.name === id)

			if (mailExists(id)) {
				if (currentMail[folder] !== id) setCurrentMail(folder, id)
				mailDetails.value?.reloadThread()
			} else if (mailExists(currentMail[folder])) {
				if (route.params.id !== currentMail[folder])
					router.replace({ name: `${folder}Mail`, params: { id: currentMail[folder] } })
				mailDetails.value?.reloadThread()
			} else setCurrentMail(folder, null)
		},
	})

const mails = Object.fromEntries(folders.map((folder) => [folder, createMailResource(folder)]))

const mailCountFilters = computed(() => ({
	folder: currentFolder.value,
	docstatus: ['!=', 2],
	[doctype.value === 'Incoming Mail' ? 'receiver' : 'sender']: user.data.name,
}))

const mailCount = createResource({
	url: 'frappe.client.get_count',
	auto: currentFolder.value !== 'Trash',
	makeParams: () => ({ doctype: doctype.value, filters: mailCountFilters.value }),
	cache: [`${currentFolder.value}MailCount`, user.data?.name],
})

interface SetSeenParams {
	name: string
	seen: 1 | 0
}

const setSeen = createResource({
	url: 'mail.api.mail.set_seen',
	makeParams: (values: SetSeenParams) => ({
		mail_type: getMailType() || doctype.value,
		...values,
	}),
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
	if (currentFolder.value !== 'Trash') mailCount.reload()
}

watch(() => currentFolder.value, reloadMails, { immediate: true })

onMounted(() => {
	socket.on('outgoing_mail_sent', () => reloadMails('Sent'))
	socket.on('incoming_mail_received', () => {
		reloadMails('Inbox')
		reloadMails('Spam')
	})
})

const getMailType = () =>
	mails[currentFolder.value].data.find((m) => m.name === currentMail[currentFolder.value])
		?.mail_type

const loadMoreEmails = useDebounceFn(() => {
	if (mails[currentFolder.value].hasNextPage) mails[currentFolder.value].next()
}, 500)
</script>

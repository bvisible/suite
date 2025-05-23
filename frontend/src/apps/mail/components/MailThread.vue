<template>
	<div v-if="threadID" class="relative flex h-full flex-col overflow-hidden">
		<div class="sticky top-0 z-10 flex items-center border-b bg-white p-2.5 sm:px-5">
			<Button
				icon="chevron-left"
				variant="ghost"
				class="mr-2"
				@click="setCurrentThread(mailbox, null)"
			/>
			<span
				v-if="mailThread.loading"
				class="bg-surface-gray-3 h-3.5 animate-pulse"
				:style="{
					width: `${Math.max(100, Math.random() * (isMobile ? 300 : 800))}px`,
				}"
			/>
			<template v-else>
				<h2 class="leading-5">
					{{ mailThread?.data?.[0].subject || __('[No subject]') }}
				</h2>
				<div class="ml-auto shrink-0 space-x-2">
					<Tooltip
						v-for="action in threadActions"
						:key="action.label"
						:text="action.label"
					>
						<Button variant="ghost" @click="action.onClick">
							<template #icon>
								<component :is="action.icon" class="h-4 w-4 text-gray-600" />
							</template>
						</Button>
					</Tooltip>
				</div>
			</template>
		</div>
		<div class="flex-1 overflow-y-auto">
			<MailThreadPlaceholder v-if="mailThread.loading" />

			<div v-else class="space-y-4 px-2.5 py-3 sm:px-5 sm:py-6">
				<div
					v-for="mail in mailThread.data"
					:key="mail.name"
					class="p-3"
					:class="{ 'rounded-md border': mailThread.data.length > 1 }"
				>
					<div class="flex space-x-3 border-b pb-2">
						<Avatar
							:label="mail.from_name || mail.from_email"
							:image="mail.user_image"
							size="xl"
						/>
						<div class="flex flex-1 justify-between text-xs">
							<div class="flex flex-col space-y-1">
								<div class="flex items-center space-x-1.5">
									<span class="text-base font-semibold">
										{{ mail.from_name || mail.from_email }}
									</span>
									<span v-if="mail.from_name && !isMobile" class="text-gray-600">
										{{ `<${mail.from_email}>` }}
									</span>
									<MailDetailsPopover :mail="mail" />
								</div>
								<div class="flex items-center space-x-2">
									<span class="flex items-center space-x-1">
										{{ __('To: ') + getRecipients(mail.recipients.To) }}
									</span>
									<span v-if="mail.recipients.CC?.length">
										{{ __('Cc: ') + getRecipients(mail.recipients.CC) }}
									</span>
									<span v-if="mail.recipients.BCC?.length">
										{{ __('Bcc: ') + getRecipients(mail.recipients.BCC) }}
									</span>
								</div>
							</div>
							<div class="flex items-center space-x-2 self-start">
								<MailDate :datetime="mail.received_at" />
								<Tooltip
									v-for="action in mailActions(mail).filter(
										(d) => d.condition !== false,
									)"
									:key="action.label"
									:text="action.label"
								>
									<Button variant="ghost" @click="action.onClick">
										<template #icon>
											<component
												:is="action.icon"
												class="h-4 w-4 text-gray-600"
											/>
										</template>
									</Button>
								</Tooltip>
								<Tooltip :text="__('More')">
									<Dropdown
										:options="
											moreActions(mail).filter((d) => d.condition !== false)
										"
									>
										<Button variant="ghost">
											<template #icon>
												<Ellipsis class="h-4 w-4 text-gray-600" />
											</template>
										</Button>
									</Dropdown>
								</Tooltip>
							</div>
						</div>
					</div>

					<IframeResizer
						v-if="mail.html_body"
						class="w-full"
						license="GPLv3"
						:scrolling="true"
						:src="getSrc(mail.html_body)"
					/>

					<pre v-else-if="mail.text_body" class="text-wrap pt-4 text-sm leading-5">{{
						mail.text_body
					}}</pre>

					<!-- <div v-if="mail.attachments.length" class="mt-8 flex flex-wrap space-x-2">
						<AttachmentCapsule
							v-for="attachment in mail.attachments"
							:key="attachment.name"
							:file-name="attachment.file_name"
							:file-url="attachment.file_url"
							class="mb-2"
						/>
					</div> -->
				</div>
			</div>
		</div>
		<SendMail
			v-model="showSendModal"
			:mail-i-d="draftMailID"
			:reply-details
			@reload-mails="emit('reloadMails', 'Drafts')"
		/>
	</div>

	<div v-else class="h-full overflow-hidden">
		<div
			class="m-5 flex h-[calc(100%-2.9em)] items-center justify-center rounded-md bg-gray-50"
		>
			<div class="flex flex-col items-center space-y-3">
				<NoMails class="h-16 w-16" />
				<p class="text-gray-500">
					{{ __('Select an email to view the thread.') }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, reactive, ref, watch } from 'vue'
// eslint-disable-next-line import/no-unresolved
import IframeResizer from '@iframe-resizer/vue/sfc'
import {
	Code,
	Ellipsis,
	Forward,
	Mail as MailIcon,
	Reply,
	ReplyAll,
	RotateCcw,
	SquarePen,
	Trash2,
} from 'lucide-vue-next'
import { Avatar, Button, Dropdown, Tooltip, createResource } from 'frappe-ui'

import { getRecipients } from '@/utils'
import { useScreenSize } from '@/utils/composables'
import { userStore } from '@/stores/user'
import AttachmentCapsule from '@/components/AttachmentCapsule.vue'
import NoMails from '@/components/Icons/NoMails.vue'
import MailDate from '@/components/MailDate.vue'
import MailDetailsPopover from '@/components/MailDetailsPopover.vue'
import MailThreadPlaceholder from '@/components/MailThreadPlaceholder.vue'
import SendMail from '@/components/SendMail.vue'

import type { Mail, MailType } from '@/types'

const props = defineProps<{
	mailbox: string
	threadID?: string
	type?: MailType
}>()

const emit = defineEmits(['reloadMails', 'markAsUnread', 'setThreadFolders', 'deleteThread'])

const { isMobile } = useScreenSize()
const dayjs = inject('$dayjs')
const { setCurrentThread } = userStore()

const showSendModal = ref(false)
const draftMailID = ref<string>()

const replyDetails = reactive({
	to: '',
	cc: '',
	bcc: '',
	subject: '',
	in_reply_to_mail_type: props.type,
	in_reply_to_mail_name: '',
})

const mailThread = createResource({
	url: 'mail.api.mail.get_mail_thread',
	makeParams: () => ({ thread_id: props.threadID }),
	// transform: (data: Mail[]) =>
	// 	props.currentFolder === 'Trash'
	// 		? data.filter((mail) => mail.folder === 'Trash')
	// 		: data.filter((mail) => mail.folder !== 'Trash'),
})

const reload = () => {
	if (props.threadID) mailThread.reload()
}

defineExpose({ reload })

const getSrc = (content: string) => {
	content = content.replace(
		/<blockquote>/g,
		'<button onclick="this.nextElementSibling.classList.toggle(\'hidden\');">...</button><blockquote class="hidden">',
	)

	/* eslint-disable no-useless-escape */
	const html = `
		<!DOCTYPE html>
		<html>
		<head>
			<style>
				body {
					font-family: InterVar, ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
					font-size: 13px;
					line-height: 1.25rem;
				}
				blockquote {
					margin: 8px 0;
					padding-left: 16px;
					border-left: 4px solid #e5e7eb;
				}
				button {
					background: none;
					border: none;
					cursor: pointer;
					padding: 0;
				}
				.hidden {
					display: none;
				}
				@media (max-width: 640px) {
					[style*="width:"] {
						width: auto !important;
					}
				}
			</style>
		</head>
		<body>
			${content}
			<script>
				document.addEventListener('click', (e) => {
					if (e.target.tagName === 'A') {
						e.preventDefault();
						window.open(e.target.href, '_blank');
					}
				});
			<\/script>
			<script
			src="https://cdn.jsdelivr.net/npm/@iframe-resizer/child@5.4.4"
			type="text/javascript"
			async
			><\/script>
		</body>
		</html>
	`

	const blob = new Blob([html], { type: 'text/html' })
	return URL.createObjectURL(blob)
}

type ActionType = 'editDraft' | 'reply' | 'replyAll' | 'forward'

interface MailAction {
	label: string
	onClick: () => void
	icon: typeof SquarePen
	condition?: boolean | (() => boolean)
}

const threadActions = computed((): MailAction[] =>
	[
		{
			label: __('Move to Trash'),
			onClick: () => emit('setThreadFolders', true),
			icon: Trash2,
			condition: props.mailbox !== 'trash',
		},
		{
			label: __('Delete Thread'),
			onClick: () => emit('deleteThread'),
			icon: Trash2,
			condition: props.mailbox === 'trash',
		},
		{
			label: __('Restore'),
			onClick: () => emit('setThreadFolders', false),
			icon: RotateCcw,
			condition: props.mailbox === 'trash',
		},
		{
			label: __('Mark as Unread'),
			onClick: () => emit('markAsUnread'),
			icon: MailIcon,
		},
	].filter((action) => action.condition !== false),
)

const mailActions = (mail: Mail): MailAction[] => [
	{
		label: __('Edit Draft'),
		onClick: () => {
			draftMailID.value = mail.name
			showSendModal.value = true
		},
		icon: SquarePen,
		condition: mail.folder === 'Drafts',
	},
	{
		label: __('Reply'),
		onClick: () => openModal('reply', mail),
		icon: Reply,
		condition: mail.status !== 'Draft',
	},
]

const moreActions = (mail: Mail): MailAction[] => [
	{
		label: __('Reply All'),
		onClick: () => openModal('replyAll', mail),
		icon: ReplyAll,
		condition: () => mail.status !== 'Draft',
	},
	{
		label: __('Forward'),
		onClick: () => openModal('forward', mail),
		icon: Forward,
		condition: () => mail.status !== 'Draft',
	},
	{
		label: __('See MIME Message'),
		onClick: () =>
			window
				.open(
					`/mail/mime-message/${mail.mail_type.toLowerCase().split(' ').join('-')}/${mail.name}`,
					'_blank',
				)
				?.focus(),
		icon: Code,
		condition: () => mail.status !== 'Draft' && !isMobile.value,
	},
	{
		label: __('Move to Trash'),
		onClick: () => setFolder.submit({ mail, moveToTrash: true }),
		icon: Trash2,
		condition: () => mail.folder !== 'Trash',
	},
	{
		label: __('Restore'),
		onClick: () => setFolder.submit({ mail, moveToTrash: false }),
		icon: RotateCcw,
		condition: () => mail.folder === 'Trash',
	},
	{
		label: __('Delete Message'),
		onClick: () => deleteMail.submit(mail),
		icon: Trash2,
		condition: () => mail.folder === 'Trash',
	},
]

const setFolder = createResource({
	url: 'mail.api.mail.set_folder',
	method: 'POST',
	makeParams: ({ mail, moveToTrash }: { mail: Mail; moveToTrash: boolean }) => ({
		mail_type: mail.mail_type,
		name: mail.name,
		move_to_trash: moveToTrash,
	}),
	onSuccess: () => emit('reloadMails'),
})

const deleteMail = createResource({
	url: 'mail.api.mail.delete_or_cancel_mails',
	makeParams: (mail: Mail) => ({
		mails: [
			{
				mail_type: mail.mail_type,
				name: mail.name,
				docstatus: mail.docstatus,
			},
		],
	}),
	onSuccess: () => emit('reloadMails'),
})
const openModal = (type: ActionType, mail) => {
	if (props.type == 'Incoming Mail') {
		replyDetails.to = mail.reply_to || mail.sender
	} else {
		replyDetails.to = mail.to.map((to) => to.email).join(', ')
	}

	replyDetails.subject = mail.subject.startsWith('Re: ') ? mail.subject : `Re: ${mail.subject}`
	replyDetails.cc = ''
	replyDetails.bcc = ''
	replyDetails.in_reply_to_mail_name = mail.name

	if (type === 'replyAll') {
		replyDetails.cc = mail.cc.map((cc) => cc.email).join(', ')
		replyDetails.bcc = mail.bcc.map((bcc) => bcc.email).join(', ')
	}
	if (type === 'forward') {
		replyDetails.to = ''
		replyDetails.subject = `Fwd: ${mail.subject}`
	}
	replyDetails.html = getReplyHtml(mail.body_html, mail.creation)
	showSendModal.value = true
}

const getReplyHtml = (html, creation) => {
	const replyHeader = `
        On ${dayjs(creation).format('DD MMM YYYY')} at ${dayjs(creation).format('h:mm A')}, ${
			replyDetails.to
		} wrote:
    `
	return `<br><blockquote>${replyHeader} <br> ${html}</blockquote>`
}

watch(() => props.threadID, reload)
</script>

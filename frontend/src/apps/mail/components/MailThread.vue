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

					<Tooltip :text="__('Move To')">
						<Dropdown :options="moveToOptions">
							<Button variant="ghost">
								<template #icon>
									<component :is="FolderInput" class="h-4 w-4 text-gray-600" />
								</template>
							</Button>
						</Dropdown>
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
									<MailDetailsPopover v-if="!mail.draft" :mail="mail" />
								</div>
								<div class="flex items-center space-x-2">
									<span v-if="mail.recipients.To?.length">
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
									v-for="action in mailActions(mail).filter((d) => d.condition)"
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

					<div v-if="mail.attachments?.length" class="mt-8 flex flex-wrap space-x-2">
						<AttachmentCapsule
							v-for="attachment in mail.attachments"
							:key="attachment.name"
							:file-name="attachment.filename"
							:blob-i-d="attachment.blob_id"
							:type="attachment.type"
							class="mb-2"
						/>
					</div>
				</div>
			</div>
		</div>
		<SendMail
			v-model="showSendModal"
			:mail-i-d="draftMailID"
			:mail-details
			@reload-mails="emit('reloadMails')"
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
	FolderInput,
	Forward,
	Mail as MailIcon,
	Reply,
	ReplyAll,
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

import type { Mail } from '@/types'

const { mailbox, threadID } = defineProps<{ mailbox: string; threadID?: string }>()

const emit = defineEmits(['reloadMails', 'markAsUnread', 'moveThread', 'deleteThread'])

const { isMobile } = useScreenSize()
const dayjs = inject('$dayjs')
const { setCurrentThread } = userStore()

const showSendModal = ref(false)
const draftMailID = ref<string>()

const mailDetails = reactive({
	from: '',
	to: [],
	cc: [],
	bcc: [],
	subject: '',
	body: '',
	attachments: [],
	in_reply_to: '',
	in_reply_to_id: '',
})

const mailThread = createResource({
	url: 'mail.api.mail.get_mail_thread',
	makeParams: () => ({ thread_id: threadID }),
	onSuccess: (data: Mail[]) => {
		if (mailbox === 'trash')
			mailThread.data = data.filter((mail) => mail.mailbox_role === 'trash')
		else mailThread.data = data.filter((mail) => mail.mailbox_role !== 'trash')
	},
})

const reload = () => {
	if (threadID) mailThread.reload()
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

const user = inject('$user')

const moveToOptions = computed(() =>
	user.data.mailboxes
		.filter((m) => ![mailbox, 'sent', 'drafts'].includes(m.role))
		.map((m) => ({
			label: m.name,
			onClick: () => emit('moveThread', m.role),
		})),
)

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
			onClick: () => emit('moveThread', 'trash'),
			icon: Trash2,
			condition: mailbox !== 'trash',
		},
		{
			label: __('Delete Thread'),
			onClick: () => emit('deleteThread'),
			icon: Trash2,
			condition: mailbox === 'trash',
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
		onClick: () => editDraft(mail),
		icon: SquarePen,
		condition: !!mail.draft,
	},
	{
		label: __('Reply'),
		onClick: () => reply(mail),
		icon: Reply,
		condition: !mail.draft,
	},
]

const moreActions = (mail: Mail): MailAction[] => [
	{
		label: __('Reply All'),
		onClick: () => replyAll(mail),
		icon: ReplyAll,
		condition: () =>
			!mail.draft &&
			mail.from_email !== user.data.email &&
			mail.recipients.To?.concat(mail.recipients.Cc || []).filter(
				(m) => m.email !== user.data.email,
			).length > 0,
	},
	{
		label: __('Forward'),
		onClick: () => forward(mail),
		icon: Forward,
		condition: () => !mail.draft,
	},
	{
		label: __('See MIME Message'),
		onClick: () => window.open(`/mail/mime-message/${mail.name}`, '_blank')?.focus(),
		icon: Code,
		condition: () => !mail.draft && !isMobile.value,
	},
	{
		label: __('Move to Trash'),
		onClick: () => moveMail.submit({ mail_ids: [mail.name], mailbox: 'trash' }),
		icon: Trash2,
		condition: () => mailbox !== 'trash',
	},
	{
		label: __('Delete Message'),
		onClick: () => deleteMails.submit([mail.name]),
		icon: Trash2,
		condition: () => mailbox === 'trash',
	},
]

const moveMail = createResource({
	url: 'mail.api.mail.set_mails_mailbox',
	makeParams: ({ mail_ids, mailbox }: { mail_ids: string[]; mailbox: string }) => ({
		mail_ids,
		mailbox,
	}),
	onSuccess: () => emit('reloadMails'),
})

const deleteMails = createResource({
	url: 'mail.mail.doctype.email_message.email_message.bulk_destroy',
	makeParams: (names: string[]) => ({ names }),
	onSuccess: () => emit('reloadMails'),
})

const editDraft = (mail: Mail) => {
	draftMailID.value = mail.name
	mailDetails.from = mail.from_email
	mailDetails.to = mail.recipients.To?.map((m) => m.email) || []
	mailDetails.cc = mail.recipients.Cc?.map((m) => m.email) || []
	mailDetails.bcc = mail.recipients.Bcc?.map((m) => m.email) || []
	mailDetails.subject = mail.subject || ''
	mailDetails.body = mail.html_body
	mailDetails.attachments = mail.attachments || []
	showSendModal.value = true
}

const reply = (mail: Mail) => {
	if (isUserEmail(mail.from_email))
		mailDetails.to = mail.recipients.To?.map((rcpt) => rcpt.email)
	else mailDetails.to = mail.reply_to.length ? mail.reply_to : [mail.from_email]

	setReplyDetailsAndOpenModal(mail)
}

const replyAll = (mail: Mail) => {
	if (isUserEmail(mail.from_email)) {
		mailDetails.to = mail.recipients.To?.map((rcpt) => rcpt.email) || []
		mailDetails.cc = mail.recipients.Cc?.map((rcpt) => rcpt.email) || []
	} else {
		mailDetails.to = mail.reply_to.length ? mail.reply_to : [mail.from_email]

		const originalRecipients = [...(mail.recipients.To || []), ...(mail.recipients.Cc || [])]
		mailDetails.cc = originalRecipients
			.filter((rcpt) => !isUserEmail(rcpt.email))
			.map((rcpt) => rcpt.email)
	}

	setReplyDetailsAndOpenModal(mail)
}

const forward = (mail: Mail) => {
	mailDetails.subject = `Fwd: ${mail.subject}`
	mailDetails.body = getMailBody(mail)
	showSendModal.value = true
}

const isUserEmail = (email: string) => user.data.email_addresses.includes(email)

const setReplyDetailsAndOpenModal = (mail: Mail) => {
	mailDetails.subject = mail.subject.startsWith('Re: ') ? mail.subject : `Re: ${mail.subject}`
	mailDetails.body = getMailBody(mail)
	mailDetails.in_reply_to = mail.message_id
	mailDetails.in_reply_to_id = mail._id
	showSendModal.value = true
}

const getMailBody = (mail: Mail) => {
	if (!mail.html_body) return ''
	const replyHeader = `On ${dayjs(mail.received_at).format('DD MMM YYYY')} at ${dayjs(mail.received_at).format('h:mm A')}, ${mail.from_email} wrote:`
	return `<br><blockquote>${replyHeader} <br> ${mail.html_body}</blockquote>`
}

watch(() => threadID, reload)
</script>

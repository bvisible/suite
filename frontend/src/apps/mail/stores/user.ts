import { reactive } from 'vue'
import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

import router from '@/router'

import type { Folder, UserResource } from '@/types'

export const userStore = defineStore('mail-users', () => {
	const userResource: UserResource = createResource({
		url: 'mail.api.account.get_user_info',
		onError: (error) => {
			if (error && error.exc_type === 'AuthenticationError') router.push('/login')
		},
		auto: true,
	})

	const getParsedItem = (key: string): string | null => {
		const item = sessionStorage.getItem(key)
		return item ? JSON.parse(item) : null
	}

	const currentThread: Record<Folder, string | null> = reactive({
		Inbox: getParsedItem('currentInboxMail'),
		Sent: getParsedItem('currentSentMail'),
		Outbox: getParsedItem('currentOutboxMail'),
		Drafts: getParsedItem('currentDraftsMail'),
		Spam: getParsedItem('currentSpamMail'),
		Trash: getParsedItem('currentTrashMail'),
	})

	const setCurrentThread = (mailbox: string, thread: string | null) => {
		const itemName = `current${mailbox}Mail`
		if (thread) {
			// currentThread[mailbox] = thread
			// sessionStorage.setItem(itemName, JSON.stringify(thread))
			router.push({ name: 'Mail', params: { mailboxName: mailbox, threadID: thread } })
		} else {
			// currentThread[mailbox] = null
			// sessionStorage.removeItem(itemName)
			router.push({ name: 'Mailbox', params: { mailboxName: mailbox } })
		}
	}

	return { userResource, currentThread, setCurrentThread }
})

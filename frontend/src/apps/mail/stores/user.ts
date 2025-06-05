import { reactive } from 'vue'
import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

import router from '@/router'

import type { UserResource } from '@/types'

export const userStore = defineStore('mail-users', () => {
	const userResource: UserResource = createResource({
		url: 'mail.api.account.get_user_info',
		onError: (error) => {
			if (error && error.exc_type === 'AuthenticationError') router.push('/login')
		},
		auto: true,
	})

	const currentThread: Record<string, string | null> = reactive({})

	const setCurrentThread = (mailbox: string, thread: string | null) => {
		currentThread[mailbox] = thread
		router.push(
			thread
				? { name: 'Mail', params: { mailbox, threadID: thread } }
				: { name: 'Mailbox', params: { mailbox } },
		)
	}

	return { userResource, currentThread, setCurrentThread }
})

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

	const mailboxes = createResource({ url: 'mail.api.mail.get_mailboxes', auto: true })

	return { userResource, mailboxes }
})

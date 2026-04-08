import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

export const userStore = defineStore('calendar-user', () => {
	const userResource = createResource({
		url: 'mail.api.account.get_user_info',
		onSuccess: (data) => {
			if (data?.is_mail_user) identities.fetch()
		},
		onError: (error) => {
			if (error && error.exc_type === 'AuthenticationError')
				window.location.replace('/app/login?redirect-to=/calendar')
		},
		auto: true,
	})

	const identities = createResource({ url: 'mail.api.account.get_identities' })

	return { userResource, identities }
})

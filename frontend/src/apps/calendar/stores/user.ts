import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

import { getDataTheme } from '@/utils'

export const userStore = defineStore('calendar-user', () => {
	const userResource = createResource({
		url: 'mail.api.account.get_user_info',
		onSuccess: (data) => {
			if (data?.is_jmap_configured) identities.fetch()
			if (data?.color_scheme)
				document.documentElement.setAttribute(
					'data-theme',
					getDataTheme(data.color_scheme),
				)
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

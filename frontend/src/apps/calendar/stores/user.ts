import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

export const userStore = defineStore('calendar-user', () => {
	const accountId = ref('')

	const setAccount = (id: string) => {
		accountId.value = id
		identities.fetch()
	}

	const userResource = createResource({
		url: 'mail.api.account.get_user_info',
		onError: (error) => {
			if (error && error.exc_type === 'AuthenticationError')
				window.location.replace('/app/login?redirect-to=/calendar')
		},
		auto: true,
	})

	const account = computed(
		() => userResource.data?.accounts?.find((a) => a.id === accountId.value)?.name,
	)

	const identities = createResource({
		url: 'mail.api.account.get_identities',
		makeParams: () => ({ account: account.value }),
		cache: ['identities', accountId.value],
	})

	return { accountId, account, setAccount, userResource, identities }
})

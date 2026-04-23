import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

import { userStore } from '@/stores/user'

export const sessionStore = defineStore('calendar-session', () => {
	const { userResource } = userStore()

	const sessionUser = () => {
		const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
		let _sessionUser = cookies.get('user_id')
		if (_sessionUser === 'Guest') _sessionUser = null

		return _sessionUser
	}

	const user = ref(sessionUser())
	const isLoggedIn = computed(() => !!user.value)

	const logout = createResource({
		url: 'logout',
		onSuccess() {
			userResource.reset()
			user.value = null
			window.location.replace('/mail/login')
		},
	})

	const branding = createResource({
		url: 'mail.api.get_branding',
		cache: 'brand',
		auto: true,
		onSuccess: (data) => (document.querySelector("link[rel='icon']").href = data.favicon),
	})

	return { isLoggedIn, logout, branding }
})

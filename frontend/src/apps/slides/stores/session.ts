import { computed, reactive } from 'vue'

import { call } from 'frappe-ui'

const sessionUser = () => {
	const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
	let _sessionUser = cookies.get('user_id')
	if (_sessionUser === 'Guest') {
		_sessionUser = null
	}
	return _sessionUser
}

const setIsSlidesUser = async () => {
	if (session.isSlidesUser !== null) return

	if (!session.isLoggedIn) {
		session.isSlidesUser = false
		return
	}

	try {
		const response = await call('slides.api.is_slides_user')
		session.isSlidesUser = response == true
	} catch (error) {
		console.error('Failed to check Slides User role:', error)
		session.isSlidesUser = false
	}
}

export const session = reactive({
	user: sessionUser(),
	isLoggedIn: computed((): boolean => !!session.user),
	isSlidesUser: null as boolean | null,
	setIsSlidesUser,
})

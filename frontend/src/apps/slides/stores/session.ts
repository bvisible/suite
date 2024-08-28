import { computed, reactive } from 'vue'

const sessionUser = () => {
	const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
	let _sessionUser = cookies.get('user_id')
	if (_sessionUser === 'Guest') {
		_sessionUser = null
	}
	return _sessionUser
}

export const session = reactive({
	user: sessionUser(),
	isLoggedIn: computed((): boolean => !!session.user),
})

import { toast } from 'frappe-ui'

export const isEmail = (s: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)

export const raiseToast = (message: string, type = 'success') => {
	if (type === 'success') return toast.success(message)

	const div = document.createElement('div')
	div.innerHTML = message
	// strip html tags
	const text =
		div.textContent || div.innerText || __('Failed to perform action. Please try again later.')
	toast.error(text)
}

export const raisePromiseToast = (
	action: () => Promise<unknown>,
	loading: string,
	success: string,
	undoAction?: () => void,
) => {
	toast.removeAll()

	const error = __('Action failed. Please try again later.')

	if (undoAction)
		return toast.promise(action(), {
			loading,
			success,
			error,
			successAction: { label: __('Undo'), onClick: () => undoAction() },
		})

	toast.promise(action(), { loading, success, error })
}

export const isUrl = (str: string) => {
	if (typeof str !== 'string' || !str.trim()) return false
	str = str.trim()
	try {
		const url = new URL(/^https?:\/\//i.test(str) ? str : 'https://' + str)
		if (url.protocol !== 'http:' && url.protocol !== 'https:') return false
		const parts = url.hostname.split('.')
		return parts.length >= 2 && parts.every((p) => p.length > 0)
	} catch {
		return false
	}
}

export const getReorderedParticipants = (
	participants,
	organizerEmail,
	originalParticipants?: any[],
) => {
	const original = new Set(originalParticipants?.map((p) => p.email) || [])

	const organizer = participants.find((p) => p.email === organizerEmail)
	const rest = participants
		.filter((p) => p.email !== organizerEmail)
		.map((p) => ({ ...p, isOrganizer: false, isNew: !original.has(p.email) }))

	return organizer ? [{ ...organizer, isOrganizer: true }, ...rest] : rest
}

export const getSystemTheme = () =>
	window.matchMedia('(prefers-color-scheme: dark)').matches ? 'Dark Mode' : 'Light Mode'

export const getDataTheme = (colorScheme?: 'Light Mode' | 'Dark Mode' | 'System Default') => {
	const resolved =
		!colorScheme || colorScheme === 'System Default' ? getSystemTheme() : colorScheme
	return resolved === 'Dark Mode' ? 'dark' : 'light'
}

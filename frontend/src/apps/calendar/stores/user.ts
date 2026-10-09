//// Neoffice — computed added, for isLocal below (maintenance#1387).
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

import type { UserAccount } from '@/apps/calendar/types/doctypes'

const ACCOUNT_STORAGE_KEY = 'mail-account-id'

export const userStore = defineStore('calendar-user', () => {
	const accountId = ref('')
	//// Neoffice — the account of the calendar kept in Neoffice for a desk user without a mailbox
	//// (maintenance#1387, suite/calendar/local.py), and whether it is the one open: what needs a mail
	//// account (sharing, CalDAV, invitations, writing to the participants) then stays hidden.
	const localAccountId = ref('')
	const isLocal = computed(() => !!accountId.value && accountId.value === localAccountId.value)

	const resolveAccount = (
		accounts?: UserAccount[],
		routeAccountId?: string,
		localAccount?: string | null,
	) => {
		//// Neoffice — no mail account: the calendar kept in Neoffice, never remembered under the mail app's key.
		if (!accounts?.length) {
			if (localAccount) {
				localAccountId.value = localAccount
				if (accountId.value !== localAccount) setAccount(localAccount, false)
			}
			return
		}

		// 1. Route param
		if (routeAccountId && accounts.some((a) => a.id === routeAccountId)) {
			if (routeAccountId !== accountId.value) setAccount(routeAccountId)
			return
		}

		// 2. localStorage
		const localId = localStorage.getItem(ACCOUNT_STORAGE_KEY)
		if (localId && accounts.some((a) => a.id === localId)) {
			if (localId !== accountId.value) setAccount(localId)
			return
		}

		// 3. Personal account fallback
		if (accountId.value) return
		const personalId = accounts.find((a) => a.is_personal)?.id
		if (personalId) setAccount(personalId)
	}

	//// Neoffice — `remember`: a local calendar account is not a mailbox, and the mail app shares this key.
	const setAccount = (id: string, remember = true) => {
		accountId.value = id
		if (remember) localStorage.setItem(ACCOUNT_STORAGE_KEY, id)
		participantIdentities.fetch()
	}

	const userResource = createResource({
		url: 'suite.mail.api.account.get_user_info',
		//// Neoffice — with the local calendar account (maintenance#1387).
		onSuccess: (data) => resolveAccount(data?.accounts, undefined, data?.local_calendar_account),
		onError: (error) => {
			if (error && error.exc_type === 'AuthenticationError')
				window.location.replace('/login?redirect-to=/calendar')
		},
		auto: true,
	})

	const participantIdentities = createResource({
		url: 'suite.mail.api.account.get_participant_identities',
		makeParams: () => ({ account: accountId.value }),
		cache: ['participantIdentities', accountId.value],
	})

	//// Neoffice — isLocal added (maintenance#1387).
	return { accountId, isLocal, resolveAccount, userResource, participantIdentities }
})

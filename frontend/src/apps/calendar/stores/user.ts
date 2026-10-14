import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { useStorage } from '@vueuse/core'
import { createResource } from 'frappe-ui'

import type { ParticipantIdentity, UserAccount } from '@/apps/calendar/types/doctypes'
import { calendarColor } from '@/apps/calendar/utils/calendars'
import type { CalendarRow } from '@/apps/calendar/utils/calendars'
//// Neoffice — the dates of the ERP come in the list of calendars as calendars of their own (maintenance#1428).
import { isErpCalendar } from '@/apps/calendar/utils/erpDates'

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
		//// Neoffice — the calendar kept in Neoffice arrives apart from the mail accounts (maintenance#1387).
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
		//// Neoffice — the calendar kept in Neoffice answers calendar methods only: it has no mail identities to
		//// ask for (maintenance#1387, suite/calendar/local.py HANDLERS).
		if (id !== localAccountId.value) identities.fetch()
		participantIdentities.fetch()
		calendars.fetch()
	}

	const userResource = createResource({
		url: 'suite.mail.api.account.get_user_info',
		// Only the accounts with a calendar the user can write to: one that only shares calendars
		// with them is under Shared Calendars, not an account to switch to. All of them stay in
		// `all_accounts`, to name where a shared calendar is from. In place, so onSuccess — handed
		// the response rather than this — reads the same list.
		transform: (data) => {
			if (data?.accounts) {
				data.all_accounts = data.accounts
				data.accounts = data.accounts.filter((account) => account.in_calendar)
			}
			return data
		},
		//// Neoffice — with the local calendar account (maintenance#1387).
		onSuccess: (data) => resolveAccount(data?.accounts, undefined, data?.local_calendar_account),
		onError: (error) => {
			if (error && error.exc_type === 'AuthenticationError')
				window.location.replace('/login?redirect-to=/calendar')
		},
		auto: true,
	})

	// The account's mail identities: the addresses it can send from.
	const identities = createResource({
		url: 'suite.mail.api.account.get_identities',
		makeParams: () => ({ account: accountId.value }),
		cache: ['identities', accountId.value],
	})

	const participantIdentities = createResource({
		url: 'suite.mail.api.account.get_participant_identities',
		makeParams: () => ({ account: accountId.value }),
		cache: ['participantIdentities', accountId.value],
	})

	// The account's calendars, and those shared with the user from other accounts. One list
	// for the grid, the sidebar, the event form and settings, so a calendar added or renamed
	// in one is there in the others.
	const calendars = createResource<CalendarRow[]>({
		url: 'suite.calendar.api.get_calendars_with_shared',
		//// Neoffice — `erp_dates`: the dates of the ERP (tasks, leaves, bookings...) follow the person's own
		//// calendars, as read-only calendars of their own (maintenance#1428, suite/calendar/sources.py). Only the
		//// calendar app asks: the mail sidebar and Meet read other lists.
		makeParams: () => ({ account: accountId.value, erp_dates: 1 }),
		cache: ['calendars', accountId.value],
		transform: (rows: CalendarRow[]) =>
			rows.map((cal) =>
				//// Neoffice — a source of the ERP's dates keeps what the server says: its switch is kept by the app
				//// that provides it, and the entries of a source that is off are not sent (maintenance#1428). The
				//// hidden list of this browser is for a calendar shared read-only.
				cal.may_write_all || isErpCalendar(cal)
					? cal
					: { ...cal, visible: hiddenShared.value.includes(cal.name) ? 0 : 1 },
			),
	})

	// Showing or hiding a calendar is its own `isVisible`, which the mail server only lets
	// someone who can write to it change — so a calendar shared read-only is hidden in this
	// browser instead.
	const hiddenShared = useStorage<string[]>('calendar-hidden-shared', [])

	// The calendars as select options, keyed by `account|id`, each in the colour it is drawn in.
	// A calendar shared from another account names that account beneath.
	const calendarOptions = computed(() => {
		const accounts: UserAccount[] = userResource.data?.all_accounts ?? []
		return (
			(calendars.data ?? [])
				//// Neoffice — the dates of the ERP are no calendar of the mail server: not a place for an event, nor
				//// something to search in, to import into or to export (maintenance#1428).
				.filter((cal) => !isErpCalendar(cal))
				.map((cal) => ({
					label: cal._name,
					description:
						cal.account === accountId.value
							? undefined
							: accounts.find((a) => a.id === cal.account)?._name,
					value: cal.name,
					account: cal.account,
					color: calendarColor(calendars.data, cal.name),
					writable: !!cal.may_write_all,
				}))
		)
	})

	// One account's calendars, keyed by their bare id, for what works on a single account:
	// import and export.
	const accountCalendarOptions = (account: string) =>
		calendarOptions.value
			.filter((option) => option.account === account)
			.map((option) => ({ ...option, value: option.value.split('|')[1] }))

	// The organizer of a new event. Invites go out as mail from the organizer's address,
	// so only a participant identity that is also a mail identity qualifies. Among those
	// the one flagged default wins, else the first. Undefined until both lists have
	// loaded, or when no address is on both.
	const organizerIdentity = computed<ParticipantIdentity | undefined>(() => {
		const sendable = new Set<string>((identities.data ?? []).map((i: { email: string }) => i.email))
		const candidates: ParticipantIdentity[] = (participantIdentities.data ?? []).filter((i) =>
			sendable.has(i.email),
		)
		return candidates.find((i) => i.default) ?? candidates[0]
	})

	return {
		accountId,
		//// Neoffice — isLocal added (maintenance#1387).
		isLocal,
		resolveAccount,
		userResource,
		identities,
		participantIdentities,
		calendars,
		hiddenShared,
		calendarOptions,
		accountCalendarOptions,
		organizerIdentity,
	}
})

export * from './doctypes'

export interface User {
	name: string
	email: string
	full_name: string
	user_type: string

	username: string | null
	user_image: string | null
	api_key: string | null
	tenant: string | null
	default_outgoing: string | null

	enabled: boolean
	is_mail_user: boolean
	is_mail_admin: boolean
	is_mail_owner: boolean

	tenant_name?: string
	roles: string[]
	mailboxes: { id: string; name: string; role: string }[]
}

export interface UserResource {
	data: User
}

export type LayoutType = 'split' | 'full'

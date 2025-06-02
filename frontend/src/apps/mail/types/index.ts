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

export interface Recipient {
	email: string
	display_name: string | null
}

export interface Attachment {
	filename: string
	blob_id: string
	type: string
	size: string
	file_url: string | null
	disposition: string
}

export interface Mail {
	name: string
	message_id: string
	_id: string
	from_name: string
	from_email: string
	subject: string
	html_body: string
	text_body: string
	received_at: string
	draft: 0 | 1
	has_attachment: 0 | 1
	recipients: {
		To: Recipient[]
		Cc: Recipient[]
		Bcc: Recipient[]
	}
	attachments: Attachment[]
}

export type LayoutType = 'split' | 'full'

interface DocType {
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
}

interface ChildDocType extends DocType {
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
}

// Last updated: 2025-11-20 15:22:07.630230
export interface EmailAddress extends ChildDocType {
	/** Display Name: Data */
	display_name?: string
	/** Email: Data */
	email: string
}

// Last updated: 2026-04-17 13:35:58.399195
export interface Identity extends DocType {
	/** May Delete: Check */
	may_delete: 0 | 1
	/** Identity ID: Data */
	id?: string
	/** Name: Data */
	_name?: string
	/** Email: Data */
	email: string
	/** Bcc: Table (Email Address) */
	bcc: EmailAddress[]
	/** Reply To: Table (Email Address) */
	reply_to: EmailAddress[]
	/** HTML: HTML Editor */
	html_signature?: any
	/** Text: Code */
	text_signature?: string
	/** Account: Select */
	account: any
	/** User: Link (User) */
	user?: string
}

// Last updated: 2026-04-15 08:27:17.244854
export interface UserAccount extends DocType {
	/** User: Link (User) */
	user: string
	/** Name: Data */
	_name: string
	/** Personal: Check */
	is_personal: 0 | 1
	/** Readonly: Check */
	is_read_only: 0 | 1
	/** Account ID: Data */
	id: string
	/** Capabilities: JSON */
	capabilities?: any
}

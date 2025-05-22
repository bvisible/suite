/* eslint-disable @typescript-eslint/no-explicit-any */

interface DocType {
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
}

interface ChildDocType extends DocType {
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
}

// Last updated: 2025-02-19 19:18:44.222087
export interface MailRecipient extends ChildDocType {
	/** Display Name: Data */
	display_name?: string
	/** Status: Select */
	status?: '' | 'Blocked' | 'Sent'
	/** Type: Select */
	type: 'To' | 'Cc' | 'Bcc'
	/** Email: Data */
	email: string
	/** Error Message: Code */
	error_message?: string
}

// Last updated: 2025-02-03 17:11:14.640642
export interface MailHeader extends ChildDocType {
	/** Key: Data */
	key: string
	/** Value: Text */
	value?: string
}

// Last updated: 2025-05-12 14:47:02.245748
export interface OutgoingMail extends DocType {
	/** Sender: Link (Mail Account) */
	sender?: string
	/** Recipients: Table (Mail Recipient) */
	recipients: MailRecipient[]
	/** Subject: Data */
	subject?: string
	/** Status: Select */
	status:
		| 'Draft'
		| 'Pending'
		| 'Queued'
		| 'Blocked'
		| 'Accepted'
		| 'Transferring'
		| 'Failed'
		| 'Sent'
		| 'Cancelled'
	/** Domain Name: Link (Mail Domain) */
	domain_name?: string
	/** Body Plain: Code */
	body_plain?: string
	/** Body HTML: HTML Editor */
	body_html?: any
	/** Custom Headers: Table (Mail Header) */
	custom_headers: MailHeader[]
	/** Amended From: Link (Outgoing Mail) */
	amended_from?: string
	/** Created At: Datetime */
	created_at?: string
	/** Message Size (Bytes): Int */
	message_size?: number
	/** IP Address: Data */
	ip_address?: string
	/** API: Check */
	via_api: 0 | 1
	/** Reply To: Data */
	reply_to?: string
	/** Folder: Select */
	folder: 'Drafts' | 'Outbox' | 'Sent' | 'Trash'
	/** Submitted At: Datetime */
	submitted_at?: string
	/** Submitted After (Seconds): Float */
	submitted_after?: number
	/** Display Name: Data */
	display_name?: string
	/** Newsletter: Check */
	is_newsletter: 0 | 1
	/** In Reply To Mail Type: Select */
	in_reply_to_mail_type?: '' | 'Incoming Mail' | 'Outgoing Mail'
	/** In Reply To Mail Name: Data */
	in_reply_to_mail_name?: string
	/** In Reply To (Message ID): Data */
	in_reply_to?: string
	/** Transfer Completed At: Datetime */
	transfer_completed_at?: string
	/** Transfer Completed After (Seconds): Float */
	transfer_completed_after?: number
	/** Transfer Started At: Datetime */
	transfer_started_at?: string
	/** Transfer Started After (Seconds): Float */
	transfer_started_after?: number
	/** Error Message: Code */
	error_message?: string
	/** Error Log: Code */
	error_log?: string
	/** Failed Count: Int */
	failed_count?: number
	/** Retry After: Datetime */
	retry_after?: string
	/** Raw Message: Link (MIME Message) */
	_raw_message?: string
	/** Message: Link (MIME Message) */
	_message?: string
	/** Priority: Int */
	priority?: number
	/** Spam Score: Float */
	spam_score?: number
	/** Is Spam: Check */
	is_spam: 0 | 1
	/** Message ID: Data */
	message_id?: string
	/** Spam Check Log: Link (Spam Check Log) */
	spam_check_log?: string
	/** Processed At: Datetime */
	processed_at?: string
	/** Processed After (Seconds): Float */
	processed_after?: number
	/** From: Data */
	from_: string
	/** Cluster: Data */
	cluster?: string
	/** Seen: Check */
	seen: 0 | 1
	/** Trashed On: Datetime */
	trashed_on?: string
}

// Last updated: 2025-03-06 14:16:22.896149
export interface IncomingMail extends DocType {
	/** Amended From: Link (Incoming Mail) */
	amended_from?: string
	/** Subject: Data */
	subject?: string
	/** Body HTML: HTML Editor */
	body_html?: any
	/** Body Plain: Code */
	body_plain?: string
	/** Message ID: Data */
	message_id?: string
	/** Display Name: Data */
	display_name?: string
	/** Sender: Data */
	sender?: string
	/** SPF Description: Small Text */
	spf_description?: string
	/** DKIM Description: Small Text */
	dkim_description?: string
	/** DMARC Description: Small Text */
	dmarc_description?: string
	/** Receiver: Link (Mail Account) */
	receiver?: string
	/** Recipients: Table (Mail Recipient) */
	recipients: MailRecipient[]
	/** Created At: Datetime */
	created_at?: string
	/** Message Size (Bytes): Int */
	message_size?: number
	/** Reply To: Data */
	reply_to?: string
	/** Folder: Select */
	folder: 'Inbox' | 'Spam' | 'Trash'
	/** Processed At: Datetime */
	processed_at?: string
	/** Processed After (Seconds): Float */
	processed_after?: number
	/** SPF: Check */
	spf_pass: 0 | 1
	/** DKIM: Check */
	dkim_pass: 0 | 1
	/** DMARC: Check */
	dmarc_pass: 0 | 1
	/** Domain Name: Link (Mail Domain) */
	domain_name?: string
	/** From IP: Data */
	from_ip?: string
	/** From Host: Data */
	from_host?: string
	/** In Reply To Mail Type: Select */
	in_reply_to_mail_type?: '' | 'Incoming Mail' | 'Outgoing Mail'
	/** In Reply To Mail Name: Data */
	in_reply_to_mail_name?: string
	/** In Reply To (Message ID): Data */
	in_reply_to?: string
	/** Fetched At: Datetime */
	fetched_at?: string
	/** Fetched After (Seconds): Float */
	fetched_after?: number
	/** Spam Score: Float */
	spam_score?: number
	/** Is Spam: Check */
	is_spam: 0 | 1
	/** Message: Link (MIME Message) */
	_message?: string
	/** Status: Select */
	status: 'Draft' | 'Submitted' | 'Cancelled'
	/** Type: Select */
	type: 'Mail' | 'DSN Report' | 'DMARC Report'
	/** Delivered To: Data */
	delivered_to?: string
	/** Cluster: Data */
	cluster?: string
	/** Seen: Check */
	seen: 0 | 1
	/** Trashed On: Datetime */
	trashed_on?: string
}

// Last updated: 2025-04-05 17:13:59.621031
export interface MailAccountRequest extends DocType {
	/** Request Key: Data */
	request_key?: string
	/** Email: Data */
	email: string
	/** Tenant: Link (Mail Tenant) */
	tenant?: string
	/** OTP: Data */
	otp?: string
	/** Invited By: Link (User) */
	invited_by?: string
	/** Is Verified: Check */
	is_verified: 0 | 1
	/** Is Expired: Check */
	is_expired: 0 | 1
	/** Is Invite: Check */
	is_invite: 0 | 1
	/** Account: Data */
	account?: string
	/** Domain: Link (Mail Domain) */
	domain_name?: string
	/** Is Admin: Check */
	is_admin: 0 | 1
	/** Send Invite: Check */
	send_invite: 0 | 1
	/** IP Address: Data */
	ip_address?: string
	/** Expires At: Datetime */
	expires_at?: string
}

// Last updated: 2025-02-03 17:11:17.517836
export interface MailDomainDNSRecord extends ChildDocType {
	/** Type: Select */
	type: '' | 'A' | 'AAAA' | 'CNAME' | 'MX' | 'TXT'
	/** Host: Data */
	host: string
	/** Value: Text */
	value: string
	/** Priority: Int */
	priority?: number
	/** TTL (Recommended): Int */
	ttl: number
	/** Category: Select */
	category: '' | 'Sending Record' | 'Receiving Record' | 'Tracking Record' | 'Server Record'
}

// Last updated: 2025-04-09 13:32:29.722110
export interface MailDomain extends DocType {
	/** Domain Name: Data */
	domain_name: string
	/** DNS Records: Table (Mail Domain DNS Record) */
	dns_records: MailDomainDNSRecord[]
	/** Enabled: Check */
	enabled: 0 | 1
	/** Verified: Check */
	is_verified: 0 | 1
	/** Newsletter Retention (Days): Int */
	newsletter_retention?: number
	/** Subdomain: Check */
	is_subdomain: 0 | 1
	/** DKIM RSA Key Size: Select */
	dkim_rsa_key_size?: '' | '2048' | '4096'
	/** Root Domain: Check */
	is_root_domain: 0 | 1
	/** Tenant: Link (Mail Tenant) */
	tenant: string
}

// Last updated: 2025-02-19 11:48:33.501192
export interface MailAlias extends DocType {
	/** Enabled: Check */
	enabled: 0 | 1
	/** Domain Name: Link (Mail Domain) */
	domain_name: string
	/** Email: Data */
	email: string
	/** Alias For (Type): Select */
	alias_for_type: '' | 'Mail Account' | 'Mail Group'
	/** Alias For (Name): Dynamic Link (alias_for_type) */
	alias_for_name: string
	/** Tenant: Link (Mail Tenant) */
	tenant?: string
	/** Normalized Email: Data */
	normalized_email?: string
}

// Last updated: 2025-02-19 11:48:33.501192
export interface MailGroup extends DocType {
	/** Enabled: Check */
	enabled: 0 | 1
	/** Domain Name: Link (Mail Domain) */
	domain_name: string
	/** Email: Data */
	email: string
	/** Display Name: Data */
	display_name?: string
	/** Tenant: Link (Mail Tenant) */
	tenant?: string
	/** Normalized Email: Data */
	normalized_email?: string
}

// Last updated: 2025-04-09 19:30:19.375260
export interface MailTenant extends DocType {
	/** Tenant Name: Data */
	tenant_name: string
	/** Logo: Attach Image */
	logo?: string
	/** Maximum No. of Domains: Int */
	max_domains: number
	/** Maximum No. of Accounts: Int */
	max_accounts: number
	/** Maximum No. of Groups: Int */
	max_groups: number
	/** User: Link (User) */
	user: string
	/** Allow Personal Signup: Check */
	allow_personal_signup: 0 | 1
	/** Cluster: Link (Mail Cluster) */
	cluster?: string
}

// Last updated: 2025-01-31 15:53:10.550269
export interface MailTenantMember extends DocType {
	/** User: Link (User) */
	user: string
	/** Tenant: Link (Mail Tenant) */
	tenant: string
	/** Is Admin: Check */
	is_admin: 0 | 1
}

// Last updated: 2025-02-04 13:50:24.993867
export interface MailGroupMember extends DocType {
	/** Mail Group: Link (Mail Group) */
	mail_group: string
	/** Member (Type): Select */
	member_type: '' | 'Mail Account' | 'Mail Group'
	/** Member (Name): Dynamic Link (member_type) */
	member_name: string
}

// Last updated: 2025-01-28 15:33:09.730936
export interface MailDomainRequest extends DocType {
	/** Domain Name: Data */
	domain_name: string
	/** User: Link (User) */
	user: string
	/** Verification Key: Data */
	verification_key?: string
	/** Is Verified: Check */
	is_verified: 0 | 1
	/** Tenant: Link (Mail Tenant) */
	tenant: string
}

// Last updated: 2025-05-12 14:42:35.868073
export interface MailAccount extends DocType {
	/** Enabled: Check */
	enabled: 0 | 1
	/** Create Mail Contact: Check */
	create_mail_contact: 0 | 1
	/** Domain Name: Link (Mail Domain) */
	domain_name: string
	/** User: Link (User) */
	user: string
	/** Email: Data */
	email?: string
	/** Display Name: Data */
	display_name?: string
	/** Reply To: Data */
	reply_to?: string
	/** Override Display Name (API): Check */
	override_display_name_api: 0 | 1
	/** Override Reply To (API): Check */
	override_reply_to_api: 0 | 1
	/** Password: Password */
	password?: string
	/** Secret: Small Text */
	secret?: string
	/** Default Email: Data */
	default_outgoing_email?: string
	/** Tenant: Link (Mail Tenant) */
	tenant?: string
	/** Normalized Email: Data */
	normalized_email?: string
	/** Backup Email: Data */
	backup_email: string
}

// Last updated: 2025-03-26 11:43:10.481605
export interface PersonalSignupDomain extends ChildDocType {
	/** Domain Name: Link (Mail Domain) */
	domain_name: string
}

// Last updated: 2025-04-08 09:33:16.800557
export interface MailSettings extends DocType {
	/** Root Domain Name: Data */
	root_domain_name: string
	/** SPF Host: Data */
	spf_host: string
	/** DNS Provider: Select */
	dns_provider?:
		| ''
		| 'AmazonRoute53'
		| 'DigitalOcean'
		| 'Cloudflare'
		| 'Hetzner'
		| 'Linode'
		| 'Namecheap'
		| 'GoDaddy'
	/** Token: Password */
	dns_provider_token?: string
	/** TTL: Int */
	default_ttl: number
	/** Host: Data */
	spamd_host?: string
	/** Port: Int */
	spamd_port?: number
	/** Scanning Mode: Select */
	spamd_scanning_mode?: 'Exclude Attachments' | 'Include Attachments' | 'Hybrid Approach'
	/** Hybrid Scanning Threshold: Float */
	spamd_hybrid_scanning_threshold?: number
	/** Enable Spam Detection: Check */
	enable_spamd: 0 | 1
	/** Enable: Check */
	enable_spamd_for_outbound: 0 | 1
	/** Block Spam: Check */
	spamd_outbound_block: 0 | 1
	/** Threshold: Float */
	spamd_outbound_threshold?: number
	/** Maximum Newsletter Retention (Days): Int */
	max_newsletter_retention: number
	/** Newsletter Retention (Days): Int */
	default_newsletter_retention: number
	/** DKIM RSA Key Size: Select */
	default_dkim_rsa_key_size: '' | '2048' | '4096'
	/** Maximum Number of Recipients: Int */
	max_recipients: number
	/** Maximum Message Size (MB): Int */
	max_message_size_mb: number
	/** Maximum Custom Headers: Int */
	max_headers: number
	/** Maximum Attachment Size (MB): Int */
	max_attachment_size_mb: number
	/** Maximum Total Attachments Size (MB): Int */
	max_total_attachments_size_mb: number
	/** Maximum Number of Attachments: Int */
	max_attachments: number
	/** Inactivity Timeout (Seconds): Int */
	smtp_inactivity_timeout: number
	/** Session Duration (Seconds): Int */
	smtp_session_duration: number
	/** Maximum Number of Messages: Int */
	smtp_max_messages: number
	/** Maximum Number of Connections: Int */
	smtp_max_connections: number
	/** Cleanup Interval (Seconds): Int */
	smtp_cleanup_interval: number
	/** Maximum Number of Connections: Int */
	imap_max_connections: number
	/** Cleanup Interval (Seconds): Int */
	imap_cleanup_interval: number
	/** Authenticated Session Timeout (Seconds): Int */
	imap_authenticated_timeout: number
	/** Unauthenticated Session Timeout (Seconds): Int */
	imap_unauthenticated_timeout: number
	/** Idle Session Timeout (Seconds): Int */
	imap_idle_timeout: number
	/** Allow Business Signup: Check */
	allow_business_signup: 0 | 1
	/** Allow Personal Signup: Check */
	allow_personal_signup: 0 | 1
	/** Personal Signup Domains: Table MultiSelect (Personal Signup Domain) */
	personal_signup_domains: PersonalSignupDomain[]
	/** Username: Data */
	dns_provider_username?: string
	/** Zone ID: Data */
	dns_provider_zone_id?: string
	/** Key: Data */
	dns_provider_key?: string
	/** Secret: Password */
	dns_provider_secret?: string
	/** Client IP: Data */
	dns_provider_client_ip?: string
	/** Private Zone: Check */
	dns_provider_private_zone: 0 | 1
	/** Access Key: Data */
	dns_provider_access_key?: string
	/** Access Secret: Password */
	dns_provider_access_secret?: string
}

// Last updated: 2024-11-16 15:35:35.197481
export interface MailContact extends DocType {
	/** User: Link (User) */
	user: string
	/** Email: Data */
	email: string
	/** Display Name: Data */
	display_name?: string
}

// Last updated: 2025-05-08 18:28:38.329228
export interface EmailMessageRecipient extends ChildDocType {
	/** Type: Select */
	type: 'To' | 'Cc' | 'Bcc'
	/** Display Name: Data */
	display_name?: string
	/** Email: Data */
	email: string
}

// Last updated: 2025-04-12 15:42:32.576799
export interface EmailMessageReplyTo extends ChildDocType {
	/** Display Name: Data */
	display_name?: string
	/** Email: Data */
	email: string
}

// Last updated: 2025-05-19 15:42:37.367950
export interface EmailMessagePart extends ChildDocType {
	/** Blob ID: Data */
	blob_id?: string
	/** Size (Bytes): Data */
	size?: string
	/** Type: Data */
	type?: string
	/** Charset: Data */
	charset?: string
	/** Disposition: Select */
	disposition?: '' | 'inline' | 'attachment'
	/** Content ID: Data */
	cid?: string
	/** Part ID: Data */
	part_id?: string
	/** Language: Data */
	language?: string
	/** Location: Data */
	location?: string
	/** File Name: Data */
	filename?: string
}

// Last updated: 2025-05-21 14:07:54.073845
export interface EmailMessage extends DocType {
	/** Subject: Small Text */
	subject?: string
	/** Account: Link (Mail Account) */
	account: string
	/** Thread ID: Data */
	thread_id?: string
	/** Sent At: Datetime */
	sent_at?: string
	/** Received At: Datetime */
	received_at?: string
	/** Has Attachment: Check */
	has_attachment: 0 | 1
	/** Folder: Data */
	folder?: string
	/** undefined: Table (Email Message Recipient) */
	recipients: EmailMessageRecipient[]
	/** Blob ID: Data */
	blob_id?: string
	/** undefined: Table (Email Message Reply To) */
	reply_to: EmailMessageReplyTo[]
	/** Message ID: Data */
	message_id?: string
	/** In Reply To (Message ID): Data */
	in_reply_to?: string
	/** From Name: Data */
	from_name?: string
	/** From Email: Data */
	from_email?: string
	/** Sender Name: Data */
	sender_name?: string
	/** Sender Email: Data */
	sender_email?: string
	/** Received After (Seconds): Int */
	received_after?: number
	/** Size (Bytes): Int */
	size?: number
	/** Seen: Check */
	seen: 0 | 1
	/** Keywords: JSON */
	_keywords?: any
	/** Attachments: Table (Email Message Part) */
	attachments: EmailMessagePart[]
	/** Message: Code */
	message?: string
	/** From IP: Data */
	from_ip?: string
	/** From Host: Data */
	from_host?: string
	/** Spam Score: Float */
	spam_score?: number
	/** SPF: Check */
	spf_pass: 0 | 1
	/** DKIM: Check */
	dkim_pass: 0 | 1
	/** DMARC: Check */
	dmarc_pass: 0 | 1
	/** SPF Description: Small Text */
	spf_description?: string
	/** DKIM Description: Small Text */
	dkim_description?: string
	/** DMARC Description: Small Text */
	dmarc_description?: string
	/** Email ID: Data */
	_id?: string
	/** Mailbox ID: Data */
	mailbox_id?: string
	/** Destroyed: Check */
	destroyed: 0 | 1
	/** Fetched After (Seconds): Int */
	fetched_after?: number
	/** Keywords: JSON */
	keywords?: any
	/** HTML Body: Table (Email Message Part) */
	_html_body: EmailMessagePart[]
	/** Text Body: Table (Email Message Part) */
	_text_body: EmailMessagePart[]
	/** HTML: Code */
	html_body?: string
	/** Text: Code */
	text_body?: string
	/** Draft: Check */
	draft: 0 | 1
	/** Mailbox Role: Data */
	mailbox_role?: string
}

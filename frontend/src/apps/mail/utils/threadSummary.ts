import type { Thread } from '@/apps/mail/types'

/**
 * A list row carries denormalised summary fields describing its thread's most recent activity —
 * derived server-side, in serialize_thread, from the latest message the view is allowed to show. When
 * a message leaves the conversation optimistically (moved, junked, deleted from the reading pane) the
 * row's own `messages` shrinks, but these fields go on describing the message that left: trashing a
 * thread's newest mail left the row previewing it, dated to it, and named after its sender until the
 * next refresh.
 *
 * This re-derives them from the conversation the row still has, and returns a closure putting the old
 * ones back — the rollback has to restore the summary, not just re-insert the message.
 *
 * `outgoingMailbox` is the current mailbox id, and only for Sent and Drafts: those rows follow the
 * latest message in the FOLDER rather than the conversation's most recent activity, so a draft reply
 * keeps its own recipients and its "Draft" badge when the thread it answers receives a newer mail (see
 * get_threads). Everywhere else the whole visible conversation is the right basis, so pass nothing.
 *
 * Two row fields are deliberately left alone:
 * - `subject`, which comes from the conversation's OPENING message (serialize_thread's `first`, taken
 *   from the whole conversation rather than from the visible subset the row carries). Removing a
 *   thread's newest mail cannot change it, and the opening message may not be in `messages` at all.
 * - `user_image`, whose row-level rule is not a message's: for a thread the user sent, the row shows
 *   the RECIPIENT's avatar (add_user_images_to_emails with is_thread=False), which needs the account's
 *   own addresses to resolve. A stale avatar until the next refresh beats guessing the wrong face.
 */
export const resummariseRow = (thread: Thread, outgoingMailbox?: string) => {
	const before = {
		from_name: thread.from_name,
		from_email: thread.from_email,
		received_at: thread.received_at,
		recipients: thread.recipients,
		draft: thread.draft,
		preview: thread.preview,
		attachments: thread.attachments,
	}
	const restore = () => void Object.assign(thread, before)

	const messages = thread.messages ?? []
	if (!messages.length) return restore

	const inMailbox = outgoingMailbox
		? messages.filter((m) => m.mailboxes.some((mb) => mb.mailbox_id === outgoingMailbox))
		: []
	// Falls back to the whole conversation rather than to nothing, exactly as the server does.
	const latest = (inMailbox.length ? inMailbox : messages).at(-1)!

	thread.from_name = latest.from_name
	thread.from_email = latest.from_email
	thread.received_at = latest.received_at
	thread.recipients = latest.recipients
	thread.draft = latest.draft
	thread.preview = latest.preview
	thread.attachments = latest.attachments

	return restore
}

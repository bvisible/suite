//// Neoffice — added file (no upstream equivalent): the words and the clock of the notes taken of a call.
// The call server answers with codes; a person reads a sentence, and the sentence never blames them.

function withZone(value: string): string {
	const text = value.includes("T") ? value : value.replace(" ", "T");
	return /(?:Z|[+-]\d\d:\d\d)$/.test(text) ? text : `${text}Z`;
}

/** The clock of the header pill: 12:04, and 1:02:03 after an hour. */
export function elapsedLabel(startedAt: string | null | undefined, now: number): string {
	if (!startedAt) return "00:00";
	const start = Date.parse(withZone(startedAt));
	if (Number.isNaN(start)) return "00:00";
	const seconds = Math.max(0, Math.floor((now - start) / 1000));
	const hours = Math.floor(seconds / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	const two = (value: number) => String(value).padStart(2, "0");
	const rest = two(seconds % 60);
	return hours > 0 ? `${hours}:${two(minutes)}:${rest}` : `${two(minutes)}:${rest}`;
}

/** What to tell somebody whose request the call server (or the instance) refused. */
export function seanceErrorMessage(code: string | undefined): string {
	switch (code) {
		case "e2ee_room":
			return __("Notes cannot be taken in an end-to-end encrypted meeting.");
		case "seance_unavailable":
			return __("This call server does not take notes yet.");
		case "not_host":
			return __("Only the host or a co-host can take notes of the meeting.");
		case "already_active":
			return __("Somebody else is already taking notes of this meeting.");
		case "no_active_seance":
			return __("Nobody is taking notes of this meeting any more.");
		case "capacity":
			return __("The call server cannot take more notes right now.");
		case "rate_limited":
			return __("Too many requests. Please try again in a moment.");
		default:
			return __("Something went wrong with the notes. Please try again.");
	}
}

/** What everybody in the call reads when the notes end. `byYou` is true for the person who ended them. */
export function seanceEndedMessage(reason: string | undefined, byYou: boolean): string {
	switch (reason) {
		case "stopped":
			return byYou
				? __("The notes are over. The minutes will arrive in a few minutes.")
				: __("The notes of this meeting are over.");
		case "room_closed":
			return __("The meeting is over, and so are the notes.");
		case "max_duration":
			return __("The notes reached their maximum length and were ended.");
		case "server_restart":
			return __("The call server restarted: the notes were interrupted. The host can start them again.");
		case "capacity":
		case "disk_error":
			return __("The notes were interrupted by the call server. What was taken is kept.");
		default:
			return __("The notes of this meeting are over.");
	}
}

/**
 * One line, for the card: how long the audio is kept (`days` is the instance's setting, counted from the
 * approval of the minutes, or from the end of the processing when nobody approves them).
 */
export function retentionSentence(days: number | null | undefined): string {
	if (days === null || days === undefined) return "";
	if (days <= 0) return __("The audio is kept with the minutes.");
	return __(
		"The audio is deleted {0} days after the minutes are approved or, if nobody approves them, after they are ready.",
		[days],
	);
}

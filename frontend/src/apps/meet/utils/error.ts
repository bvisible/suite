export function getErrorMessage(error: unknown): string {
	if (!(error instanceof Error)) {
		return normalizeErrorMessage(error);
	}

	if (
		"messages" in error &&
		Array.isArray(error.messages) &&
		error.messages.length > 0
	) {
		return normalizeErrorMessage(error.messages[error.messages.length - 1]);
	}

	// //// Neoffice — i18n: text a person reads goes through __() (#1316)
	return normalizeErrorMessage(error.message || __("An unknown error occurred"));
}

function normalizeErrorMessage(message: unknown): string {
	return String(message)
		.replace(/<[^>]+>/g, " ")
		.replace(/\s+/g, " ")
		.replace(/\s+([.,!?;:])/g, "$1")
		.trim();
}

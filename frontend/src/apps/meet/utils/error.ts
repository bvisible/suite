export function getErrorMessage(error: unknown): string {
	if (!(error instanceof Error)) {
		return String(error);
	}

	if (
		"messages" in error &&
		Array.isArray(error.messages) &&
		error.messages.length > 0
	) {
		return error.messages[error.messages.length - 1];
	}

	// //// Neoffice — i18n: text a person reads goes through __() (#1316)
	return error.message || __("An unknown error occurred");
}

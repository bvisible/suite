import type { RecordingPreflight } from "../composables/useRecording";

export function getRecordingUnavailableReason(preflight: RecordingPreflight) {
	if (!preflight.global_enabled)
		return {
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			title: __("Recording is disabled"),
			message: __("An administrator needs to enable recording for Meet."),
		};
	if (preflight.e2ee_conflict)
		return {
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			title: __("Encrypted meetings can't be recorded"),
			message: __("Turn off end-to-end encryption before enabling recording."),
		};
	if (!preflight.storage_available || preflight.budget_bytes <= 0)
		return {
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			title: __("Drive storage is unavailable"),
			message: __("The room owner needs enough available Drive storage for a recording."),
		};
	if (!preflight.recorder_available)
		return {
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			title: __("Recorder service is unavailable"),
			message: __("Try again shortly or contact your administrator."),
		};
	return {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		title: __("Recording is unavailable"),
		message: __("Check the room settings and try again."),
	};
}

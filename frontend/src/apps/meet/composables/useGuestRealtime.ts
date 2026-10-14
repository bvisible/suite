import type { Socket } from "socket.io-client";
import { request } from "../utils/request";
import {
	isUnknownRecord,
	type JoinPayload,
	normalizeJoinPayload,
} from "../types";
import type {
	GuestSessionStatus,
	StoredGuestSession,
} from "./useConnectionState";

type ActiveGuestSessionStatus = Extract<
	GuestSessionStatus,
	"pending" | "admitted"
>;
type TerminalGuestSessionStatus = Exclude<
	GuestSessionStatus,
	ActiveGuestSessionStatus
>;

interface GuestRealtimeEvent {
	guestId: string;
	meetingId: string;
}

const GUEST_SUBSCRIPTION_RETRY_DELAY = 5_000;
const GUEST_SUBSCRIPTION_MAX_RETRIES = 4;
// //// Neoffice — the reconciliation poll upstream removed: Frappe v15's realtime server loads no app handlers, so
// //// nothing answers `guest_subscribe` and a guest in the waiting room would never hear of its admission. The
// //// poll asks for the status of the session, with the guest's own proof, as it always did — and only while the
// //// realtime subscription has not been acknowledged, so a site whose server answers it never polls.
const GUEST_STATUS_RECONCILIATION_INTERVAL = 5_000;

interface GuestRealtimeLifecycleOptions {
	socket: Socket | null;
	meetingId: string;
	readSession: () => StoredGuestSession | null;
	onActiveStatus: (
		status: ActiveGuestSessionStatus,
		session: StoredGuestSession,
	) => void | Promise<void>;
	onTerminalStatus: (status: TerminalGuestSessionStatus) => void;
	onError: (error: Error) => void;
}

function isActiveSession(
	session: StoredGuestSession | null,
): session is StoredGuestSession & { status: ActiveGuestSessionStatus } {
	return session?.status === "pending" || session?.status === "admitted";
}

function normalizeGuestRealtimeEvent(value: unknown): GuestRealtimeEvent | null {
	if (
		!isUnknownRecord(value) ||
		typeof value.guest_id !== "string" ||
		typeof value.meeting_id !== "string"
	) return null;
	return { guestId: value.guest_id, meetingId: value.meeting_id };
}

function normalizeStatus(
	value: unknown,
): ActiveGuestSessionStatus | TerminalGuestSessionStatus | null {
	return value === "pending" ||
		value === "admitted" ||
		value === "rejected" ||
		value === "banned" ||
		value === "expired"
		? value
		: null;
}

export async function getApprovedGuestConnectionDetails(
	session: StoredGuestSession,
): Promise<JoinPayload> {
	const response = normalizeJoinPayload(
		await request(
			"/api/v2/method/suite.meet.api.meeting.get_approved_guest_connection_details",
			{
				meeting_id: session.meetingId,
				guest_id: session.guestId,
				guest_session_token: session.guestSessionToken,
			},
		),
	);
	if (response?.status !== "joined" || !response.auth_token) {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		throw new Error(__("Guest is not admitted to this meeting"));
	}
	if (response.guest_id && response.guest_id !== session.guestId) {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		throw new Error(__("Approved guest identity does not match the stored session"));
	}
	return response;
}

export function createGuestRealtimeLifecycle({
	socket,
	meetingId,
	readSession,
	onActiveStatus,
	onTerminalStatus,
	onError,
}: GuestRealtimeLifecycleOptions) {
	let setup = false;
	let subscribedSession: StoredGuestSession | null = null;
	let subscriptionRetryTimeout: ReturnType<typeof setTimeout> | null = null;
	let subscriptionRetryCount = 0;
	// //// Neoffice — see GUEST_STATUS_RECONCILIATION_INTERVAL.
	let reconciliationInterval: ReturnType<typeof setInterval> | null = null;
	let reconciliationInProgress = false;
	let realtimeAcknowledged = false;

	const matchesSubscribedSession = (value: unknown) => {
		const event = normalizeGuestRealtimeEvent(value);
		return Boolean(
			subscribedSession &&
				event?.guestId === subscribedSession.guestId &&
				event.meetingId === meetingId,
		);
	};

	const unsubscribe = () => {
		if (!socket || !subscribedSession) return;
		socket.emit("guest_unsubscribe", {
			guest_id: subscribedSession.guestId,
			meeting_id: meetingId,
			guest_session_token: subscribedSession.guestSessionToken,
		});
		subscribedSession = null;
		// //// Neoffice — see GUEST_STATUS_RECONCILIATION_INTERVAL.
		realtimeAcknowledged = false;
	};

	const stop = () => {
		unsubscribe();
		if (subscriptionRetryTimeout) {
			clearTimeout(subscriptionRetryTimeout);
			subscriptionRetryTimeout = null;
		}
		subscriptionRetryCount = 0;
		// //// Neoffice — the reconciliation poll stops with the lifecycle, socket or none.
		if (reconciliationInterval) {
			clearInterval(reconciliationInterval);
			reconciliationInterval = null;
		}
		if (!socket || !setup) return;
		socket.off("meet:guest_join_approved", handleApproved);
		socket.off("meet:guest_join_rejected", handleRejected);
		socket.off("connect", handleReconnect);
		setup = false;
	};

	const handleTerminalStatus = (status: TerminalGuestSessionStatus) => {
		onTerminalStatus(status);
		stop();
	};

	const handleAcknowledgement = (value: unknown) => {
		if (!isUnknownRecord(value) || typeof value.ok !== "boolean") {
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			onError(new Error(__("Invalid guest subscription acknowledgement")));
			return;
		}
		const status = normalizeStatus(value.status);
		if (value.ok) {
			subscriptionRetryCount = 0;
			// //// Neoffice — the server answers the subscription: realtime is the path, no poll.
			realtimeAcknowledged = true;
			if (!status || status === "rejected" || status === "banned" || status === "expired") {
				// //// Neoffice — i18n: text a person reads goes through __() (#1316)
				onError(new Error(__("Invalid guest subscription status")));
				return;
			}
			if (subscribedSession) void onActiveStatus(status, subscribedSession);
			return;
		}
		if (status === "rejected" || status === "banned" || status === "expired") {
			handleTerminalStatus(status);
			return;
		}
		const reason = typeof value.error === "string" ? value.error : "invalid_request";
		if (reason === "validation_failed") {
			if (subscriptionRetryCount >= GUEST_SUBSCRIPTION_MAX_RETRIES) {
				// //// Neoffice — i18n: text a person reads goes through __() (#1316)
				onError(new Error(__("Could not verify your guest session. Please reconnect.")));
				return;
			}
			if (!subscriptionRetryTimeout) {
				const delay = GUEST_SUBSCRIPTION_RETRY_DELAY * 2 ** subscriptionRetryCount;
				subscriptionRetryCount += 1;
				subscriptionRetryTimeout = setTimeout(() => {
					subscriptionRetryTimeout = null;
					subscribe();
				}, delay);
			}
			return;
		}
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		onError(new Error(__("Guest realtime subscription failed: {0}", [reason])));
	};

	const subscribe = () => {
		const session = readSession();
		if (!socket || !isActiveSession(session)) return;
		if (subscriptionRetryTimeout) {
			clearTimeout(subscriptionRetryTimeout);
			subscriptionRetryTimeout = null;
		}
		if (
			subscribedSession &&
			(subscribedSession.guestId !== session.guestId ||
				subscribedSession.guestSessionToken !== session.guestSessionToken)
		) unsubscribe();
		subscribedSession = { ...session };
		socket.emit(
			"guest_subscribe",
			{
				guest_id: session.guestId,
				meeting_id: meetingId,
				guest_session_token: session.guestSessionToken,
			},
			handleAcknowledgement,
		);
	};

	// //// Neoffice — the reconciliation poll: see GUEST_STATUS_RECONCILIATION_INTERVAL.
	const reconcile = async () => {
		const session = readSession();
		if (realtimeAcknowledged || !isActiveSession(session) || reconciliationInProgress) return;
		reconciliationInProgress = true;
		try {
			const response = await request<unknown>(
				"/api/v2/method/suite.meet.api.meeting.validate_guest_session",
				{
					meeting_id: meetingId,
					guest_id: session.guestId,
					guest_session_token: session.guestSessionToken,
				},
			);
			if (!isUnknownRecord(response)) return;
			const status = normalizeStatus(response.status);
			if (response.valid === true && (status === "pending" || status === "admitted")) {
				await onActiveStatus(status, session);
			} else if (status === "rejected" || status === "banned" || status === "expired") {
				handleTerminalStatus(status);
			} else if (response.valid === false) {
				handleTerminalStatus("expired");
			}
		} catch {
			// Realtime remains the primary path where it exists; retry transient failures at the next tick.
		} finally {
			reconciliationInProgress = false;
		}
	};

	function handleApproved(value: unknown) {
		if (matchesSubscribedSession(value) && subscribedSession) {
			void onActiveStatus("admitted", subscribedSession);
		}
	}
	function handleRejected(value: unknown) {
		if (matchesSubscribedSession(value)) handleTerminalStatus("rejected");
	}
	function handleReconnect() {
		subscriptionRetryCount = 0;
		subscribe();
	}

	const start = () => {
		const session = readSession();
		if (!socket || !isActiveSession(session)) return;
		if (
			setup &&
			subscribedSession?.guestId === session.guestId &&
			subscribedSession.guestSessionToken === session.guestSessionToken
		) return;
		if (!setup) {
			socket.on("meet:guest_join_approved", handleApproved);
			socket.on("meet:guest_join_rejected", handleRejected);
			socket.on("connect", handleReconnect);
			setup = true;
			// //// Neoffice — see GUEST_STATUS_RECONCILIATION_INTERVAL.
			reconciliationInterval = setInterval(
				() => void reconcile(),
				GUEST_STATUS_RECONCILIATION_INTERVAL,
			);
		}
		subscribe();
	};

	return { start, stop };
}

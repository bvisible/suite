//// Neoffice — added file (no upstream equivalent): taking notes of a call from Meet (a "séance").
//
// Who does what:
//   * the call server (SFU) copies the voice of the people who said yes, and tells the room who is captured;
//   * the instance (`neoffice_theme.meet_seance`) keeps the record of each person's yes and writes the minutes.
// Nothing is captured before a person's own yes: this composable never sends a consent the person did not give,
// and a host's page asks for the notes with a dialog that says the host is recorded too.
import { frappeRequest, toast } from "frappe-ui";
import { computed } from "vue";
import { isUnknownRecord } from "../types";
import type { SFUClient } from "../utils/SFUClient";
import { seanceEndedMessage, seanceErrorMessage } from "../utils/seancePresentation";
import type { SeanceAnswer, SeanceCapabilities, SeanceStore } from "./useSeanceStore";

const API = "neoffice_theme.meet_seance";
/** After a drop of the person's track (an error at the call server) the page asks again, at most this often. */
const RESUME_COOLDOWN_MS = 20_000;

/** What the page sends to the instance; a guest adds the proof of their lease. */
export interface SeanceParams {
	meet_room?: string;
	meeting?: string;
	title?: string;
	erase?: 0 | 1;
	guest_id?: string;
	guest_session_token?: string;
}

type Call = (method: string, params: SeanceParams) => Promise<unknown>;

/** What the instance says of this person's place in the running séance (`get_seance_state`). */
interface InstanceState {
	running: boolean | null;
	you: string | null;
	retentionDays: number | null;
}

interface Notifier {
	success: (message: string) => void;
	info: (message: string) => void;
	error: (message: string) => void;
}

interface SeanceDeps {
	meetingId: string;
	sfuClient: Pick<SFUClient, "sendRequest" | "on" | "off">;
	store: SeanceStore;
	/** The identifier the call server knows this person by: an account's, or `guest_<id>`. */
	currentUserId: () => string | null;
	/** The proof of a guest's lease; null for somebody signed in. */
	guestProof: () => { guest_id: string; guest_session_token: string } | null;
	call?: Call;
	notify?: Notifier;
	/** Where a "not for me" is remembered for this tab (a reload does not ask again). */
	storage?: Pick<Storage, "getItem" | "setItem">;
	now?: () => number;
}

interface SfuView {
	active: boolean;
	seanceId: string;
	startedAt: string | null;
	startedBy: { id: string; name: string } | null;
	capturing: string[];
	you: SeanceAnswer;
}

const defaultCall: Call = (method, params) => frappeRequest({ url: `${API}.${method}`, params });

const defaultNotify: Notifier = {
	success: (message) => toast.success(message),
	info: (message) => toast.info(message),
	error: (message) => toast.error(message),
};

function readInstanceState(value: unknown): InstanceState | null {
	if (!isUnknownRecord(value)) return null;
	return {
		running: typeof value.running === "boolean" ? value.running : null,
		you: typeof value.you === "string" ? value.you : null,
		retentionDays: typeof value.retention_days === "number" ? value.retention_days : null,
	};
}

function readCapabilities(value: unknown): SeanceCapabilities | null {
	if (!isUnknownRecord(value) || typeof value.enabled !== "boolean") return null;
	return {
		enabled: value.enabled,
		can_start: value.can_start === true,
		reason: typeof value.reason === "string" ? value.reason : null,
		meeting: typeof value.meeting === "string" ? value.meeting : null,
		owner: typeof value.owner === "string" ? value.owner : null,
	};
}

function readAnswer(value: unknown): SeanceAnswer {
	return value === "consented" || value === "declined" || value === "withdrawn" ? value : "pending";
}

/** The call server's view of the séance, or null when it says nothing is running (or says something odd). */
function readView(value: unknown): SfuView | null {
	if (!isUnknownRecord(value) || value.active !== true) return null;
	if (typeof value.seance_id !== "string" || !value.seance_id) return null;
	const by = isUnknownRecord(value.started_by) ? value.started_by : null;
	return {
		active: true,
		seanceId: value.seance_id,
		startedAt: typeof value.started_at === "string" ? value.started_at : null,
		startedBy:
			by && typeof by.id === "string"
				? { id: by.id, name: typeof by.name === "string" && by.name ? by.name : by.id }
				: null,
		capturing: Array.isArray(value.capturing)
			? value.capturing.filter((item): item is string => typeof item === "string")
			: [],
		you: readAnswer(value.you),
	};
}

/** A sentence for the person: the instance's own words when it refused with some, else ours for the code. */
function messageOf(error: unknown): string {
	const failure = error as { status?: unknown; messages?: unknown; message?: unknown } | null;
	const status = typeof failure?.status === "number" ? failure.status : 0;
	const messages = Array.isArray(failure?.messages) ? failure.messages : [];
	const first = messages.find((item): item is string => typeof item === "string" && item.length > 0);
	if (first && status >= 400 && status < 500) return first;
	// The call server answers with a code as the message of the error.
	return seanceErrorMessage(typeof failure?.message === "string" ? failure.message : undefined);
}

export function useSeance(deps: SeanceDeps) {
	const { meetingId, sfuClient, store } = deps;
	const call = deps.call ?? defaultCall;
	const notify = deps.notify ?? defaultNotify;
	const now = deps.now ?? Date.now;
	const storage: Pick<Storage, "getItem" | "setItem"> | null =
		deps.storage ?? (typeof sessionStorage === "undefined" ? null : sessionStorage);

	let settling: Promise<void> | null = null;
	let endedByYou = false;
	let lastResume = 0;

	// ---- what this tab remembers ----

	function declinedKey(seanceId: string) {
		return `meet-seance-declined:${seanceId}`;
	}

	function declinedHere(seanceId: string): boolean {
		try {
			return storage?.getItem(declinedKey(seanceId)) === "1";
		} catch {
			return false;
		}
	}

	function rememberDecline(seanceId: string) {
		try {
			storage?.setItem(declinedKey(seanceId), "1");
		} catch {
			// private mode: the card may come back after a reload, which is harmless
		}
	}

	function forgetDecline(seanceId: string) {
		try {
			storage?.setItem(declinedKey(seanceId), "0");
		} catch {
			// as above
		}
	}

	function guestParams(): Pick<SeanceParams, "guest_id" | "guest_session_token"> {
		return deps.guestProof() ?? {};
	}

	// ---- reading where things stand ----

	function apply(view: SfuView) {
		store.begin({
			seanceId: view.seanceId,
			startedAt: view.startedAt,
			startedBy: view.startedBy,
			capturing: view.capturing,
		});
		// The call server forgets a person's answer when they leave the room: only a firm answer is taken from it.
		if (view.you === "consented" || view.you === "declined" || view.you === "withdrawn") {
			store.you = view.you;
		}
	}

	/**
	 * Where this person stands in the running séance. The call server forgets an answer when somebody leaves the
	 * room, the instance does not: a person who agreed and came back is taken again without a new card, a person
	 * who withdrew is left alone, and anybody else is asked.
	 */
	async function settle(known?: InstanceState | null) {
		if (settling) return settling;
		settling = (async () => {
			const seanceId = store.seanceId;
			if (!store.active || !seanceId) return;
			const me = deps.currentUserId();
			if (store.you === "consented" && (!me || store.isCaptured(me))) return;
			if (store.you === "declined" || store.you === "withdrawn") return;
			let mine: InstanceState | null = known ?? null;
			if (!mine) {
				try {
					mine = readInstanceState(
						await call("get_seance_state", { meeting: seanceId, meet_room: meetingId, ...guestParams() }),
					);
				} catch {
					// The instance does not know the notes (an older site) or is away: ask the person, as anybody.
				}
			}
			if (store.seanceId !== seanceId) return;
			if (mine && mine.retentionDays !== null) store.retentionDays = mine.retentionDays;
			if (mine?.running === false) {
				// The instance has closed it (the host ended the notes here, or they were closed for want of news):
				// nothing to ask, nothing to take.
				store.end();
				return;
			}
			if (mine?.you === "agreed") {
				await resume();
			} else if (mine?.you === "withdrawn") {
				store.you = "withdrawn";
			} else if (declinedHere(seanceId)) {
				store.you = "declined";
			} else {
				store.you = "pending";
			}
		})().finally(() => {
			settling = null;
		});
		return settling;
	}

	async function refresh() {
		// The instance first: where no notes are running (the usual case, and every site that did not switch
		// them on) the call server is not even asked.
		let mine: InstanceState | null = null;
		try {
			mine = readInstanceState(await call("get_seance_state", { meet_room: meetingId, ...guestParams() }));
		} catch {
			// An older site, or a person the instance does not know: no notes to show.
		}
		if (!mine?.running) {
			if (store.active) store.end();
			return;
		}
		try {
			const view = readView(await sfuClient.sendRequest("seance:get_state", {}));
			if (!view) {
				if (store.active) store.end();
				return;
			}
			apply(view);
			await settle(mine);
		} catch {
			// A call server that does not know the notes answers with an error: there is nothing to show.
		}
	}

	async function loadCapabilities() {
		// A guest cannot start the notes (a host has an account): no request that would only be refused.
		if (deps.guestProof()) {
			store.capabilities = null;
			return;
		}
		try {
			const answer = await call("get_capabilities", { meet_room: meetingId });
			store.capabilities = readCapabilities(answer);
		} catch {
			// Not signed in, or a site without the notes: the host's button simply is not offered.
			store.capabilities = null;
		}
	}

	// ---- the person's own answer ----

	async function sendConsent(): Promise<void> {
		const seanceId = store.seanceId;
		if (!seanceId) return;
		const answer = await call("give_consent", { meeting: seanceId, ...guestParams() });
		const token = isUnknownRecord(answer) ? answer.consent_token : null;
		if (typeof token !== "string" || !token) throw new Error("no_consent_token");
		const view = readView(await sfuClient.sendRequest("seance:consent", { token }));
		if (view) apply(view);
		store.you = "consented";
		forgetDecline(seanceId);
	}

	/** Takes up again, quietly, a yes the person gave earlier (a reload, a return to the call). */
	async function resume() {
		const seanceId = store.seanceId;
		if (!seanceId) return;
		try {
			await sendConsent();
		} catch {
			// Not taken for now: the card stays available through the pill.
			if (store.seanceId === seanceId) store.you = "pending";
		}
	}

	async function agree() {
		if (!store.active || store.busy) return;
		store.busy = true;
		try {
			await sendConsent();
		} catch (error) {
			notify.error(messageOf(error));
		} finally {
			store.busy = false;
		}
	}

	async function decline() {
		const seanceId = store.seanceId;
		if (!seanceId) return;
		rememberDecline(seanceId);
		store.you = "declined";
		try {
			await sfuClient.sendRequest("seance:decline", {});
		} catch {
			// Nothing was being captured anyway.
		}
	}

	async function withdraw(erase = false) {
		const seanceId = store.seanceId;
		if (!seanceId || store.busy) return;
		store.busy = true;
		try {
			// The call server first: the voice stops at once. The instance holds the record and the erasure.
			try {
				await sfuClient.sendRequest("seance:withdraw", { erase });
			} catch {
				// The instance tells the call server itself.
			}
			await call("withdraw_consent", { meeting: seanceId, erase: erase ? 1 : 0, ...guestParams() });
			store.you = "withdrawn";
			rememberDecline(seanceId);
			notify.info(
				erase
					? __("You are no longer recorded, and what you said is being erased.")
					: __("You are no longer recorded."),
			);
		} catch (error) {
			notify.error(messageOf(error));
		} finally {
			store.busy = false;
		}
	}

	// ---- the host's side ----

	async function start(title?: string) {
		if (store.busy || store.active) return;
		store.busy = true;
		try {
			const started = await call("start_seance", { meet_room: meetingId, ...(title ? { title } : {}) });
			if (!isUnknownRecord(started) || typeof started.start_token !== "string") {
				throw new Error("no_start_token");
			}
			const meeting = String(started.meeting);
			let view: SfuView | null;
			try {
				view = readView(await sfuClient.sendRequest("seance:start", { token: started.start_token }));
			} catch (error) {
				// Refused at the call server: the séance made at the instance is ended at once, nothing waits.
				try {
					await call("stop_seance", { meeting });
				} catch {
					// the instance closes a séance the call server never saw by itself
				}
				throw error;
			}
			if (!view) throw new Error("seance_unavailable");
			apply(view);
			store.you = "pending";
			// The dialog the host confirmed says they are recorded too: that is their yes.
			await sendConsent();
		} catch (error) {
			notify.error(messageOf(error));
		} finally {
			store.busy = false;
			void loadCapabilities();
		}
	}

	async function stop() {
		const seanceId = store.seanceId;
		if (!seanceId || store.busy) return;
		store.busy = true;
		endedByYou = true;
		try {
			try {
				await sfuClient.sendRequest("seance:stop", {});
			} catch {
				// The instance tells the call server itself.
			}
			await call("stop_seance", { meeting: seanceId });
			// The call server's `seance:ended` closes it on every screen; if it never comes, this one is closed here.
			if (store.seanceId === seanceId) store.end();
			notify.success(seanceEndedMessage("stopped", true));
		} catch (error) {
			notify.error(messageOf(error));
		} finally {
			// What the call server pushes while this runs is about this stop; what comes later is not.
			endedByYou = false;
			store.busy = false;
			void loadCapabilities();
		}
	}

	// ---- what the call server pushes ----

	function onState(value: unknown) {
		if (!isUnknownRecord(value)) return;
		const view = readView({ ...value, you: undefined });
		if (!view) {
			if (value.active === false && store.active) store.end();
			return;
		}
		const wasKnown = store.active && store.seanceId === view.seanceId;
		store.begin({
			seanceId: view.seanceId,
			startedAt: view.startedAt,
			startedBy: view.startedBy,
			capturing: view.capturing,
		});
		const me = deps.currentUserId();
		if (!wasKnown) {
			void settle();
			return;
		}
		if (me && store.isCaptured(me) && store.you === "pending") store.you = "consented";
		// Our track ended without our asking (a fault at the call server): ask again, not too often.
		if (me && store.you === "consented" && !store.isCaptured(me) && now() - lastResume > RESUME_COOLDOWN_MS) {
			lastResume = now();
			void resume();
		}
	}

	function onEnded(value: unknown) {
		const reason = isUnknownRecord(value) && typeof value.reason === "string" ? value.reason : undefined;
		const byYou = endedByYou;
		endedByYou = false;
		if (!store.active) return;
		store.end();
		// The person who ended the notes was told already.
		if (!byYou) notify.info(seanceEndedMessage(reason, false));
		void loadCapabilities();
	}

	const handlers: Array<[string, (value: unknown) => void]> = [
		["seance:state", onState],
		["seance:ended", onEnded],
	];

	function setupSeanceEvents() {
		for (const [event, handler] of handlers) sfuClient.on(event, handler as (...args: unknown[]) => void);
	}

	function dispose() {
		for (const [event, handler] of handlers) sfuClient.off(event, handler as (...args: unknown[]) => void);
	}

	/** The host's button is offered: the instance said so and nothing is running. */
	const canStart = computed(() => Boolean(store.capabilities?.can_start) && !store.active);

	return {
		store,
		canStart,
		setupSeanceEvents,
		dispose,
		refresh,
		loadCapabilities,
		start,
		stop,
		agree,
		decline,
		withdraw,
	};
}

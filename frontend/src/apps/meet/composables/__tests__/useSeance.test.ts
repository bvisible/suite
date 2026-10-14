//// Neoffice — added file (no upstream equivalent): the notes of a call, from the page of each person.
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { type SeanceParams, useSeance } from "../useSeance";
import { useSeanceStore } from "../useSeanceStore";

const ME = "marie@example.test";
const SEANCE = "MTG-2026-00042";

type Handler = (value: unknown) => void;

/** The call server, as the page sees it: requests answered from a table, events pushed by the test. */
class FakeSfu {
	requests: Array<[string, unknown]> = [];
	answers = new Map<string, unknown>();
	handlers = new Map<string, Set<Handler>>();

	async sendRequest(event: string, data: unknown) {
		this.requests.push([event, data]);
		const answer = this.answers.get(event);
		if (answer instanceof Error) throw answer;
		if (typeof answer === "function") return (answer as (data: unknown) => unknown)(data);
		return answer ?? { success: true };
	}

	on(event: string, handler: Handler) {
		if (!this.handlers.has(event)) this.handlers.set(event, new Set());
		this.handlers.get(event)?.add(handler);
	}

	off(event: string, handler?: Handler) {
		if (handler) this.handlers.get(event)?.delete(handler);
		else this.handlers.delete(event);
	}

	push(event: string, value: unknown) {
		for (const handler of this.handlers.get(event) ?? []) handler(value);
	}

	sent(event: string) {
		return this.requests.filter(([name]) => name === event).map(([, data]) => data);
	}
}

interface ViewShape {
	success: boolean;
	active: boolean;
	seance_id: string;
	started_at: string;
	started_by: { id: string; name: string };
	capturing: string[];
	you: string;
}

function view(overrides: Partial<ViewShape> = {}): ViewShape {
	return {
		success: true,
		active: true,
		seance_id: SEANCE,
		started_at: "2026-10-14T10:00:00.000Z",
		started_by: { id: "host@example.test", name: "Marc Dupuis" },
		capturing: [],
		you: "pending",
		...overrides,
	};
}

/** What the instance answers a call: a value, or an error that is thrown. */
type InstanceAnswer = object | Error;

function setup(options: { guest?: boolean; calls?: Record<string, InstanceAnswer> } = {}) {
	setActivePinia(createPinia());
	const store = useSeanceStore();
	const sfu = new FakeSfu();
	const memory = new Map<string, string>();
	const notices: Array<[string, string]> = [];
	const calls: Array<[string, SeanceParams]> = [];
	const answers: Record<string, InstanceAnswer> = {
		get_seance_state: { running: true, you: "pending", retention_days: 30, meeting: SEANCE },
		give_consent: { consent_token: "consent-token", consent_at: "2026-10-14T10:01:00", meeting: SEANCE },
		withdraw_consent: { withdrawn: 1, erased: false },
		start_seance: { meeting: SEANCE, start_token: "start-token", title: "Call" },
		stop_seance: { status: "Uploading" },
		get_capabilities: { enabled: true, can_start: true, reason: null, meeting: null, owner: null },
		...(options.calls ?? {}),
	};
	const seance = useSeance({
		meetingId: "room-1",
		sfuClient: sfu as never,
		store,
		currentUserId: () => ME,
		guestProof: () =>
			options.guest ? { guest_id: ME, guest_session_token: "lease-proof" } : null,
		call: async (method, params) => {
			calls.push([method, params]);
			const answer = answers[method];
			if (answer instanceof Error) throw answer;
			return answer;
		},
		notify: {
			success: (message) => notices.push(["success", message]),
			info: (message) => notices.push(["info", message]),
			error: (message) => notices.push(["error", message]),
		},
		storage: {
			getItem: (key) => memory.get(key) ?? null,
			setItem: (key, value) => void memory.set(key, value),
		},
		now: () => 1_000_000,
	});
	return { seance, store, sfu, calls, notices, memory, answers };
}

function instanceError(message: string, status = 417) {
	return Object.assign(new Error("POST /api/method/x"), { status, messages: [message] });
}

beforeEach(() => {
	vi.clearAllMocks();
});

describe("useSeance: where the notes stand", () => {
	it("shows nothing when the call server says no notes are running", async () => {
		const { seance, store, sfu } = setup();
		sfu.answers.set("seance:get_state", { success: true, active: false });
		await seance.refresh();
		expect(store.active).toBe(false);
		expect(store.isAsked).toBe(false);
	});

	it("shows nothing, and does not fail, on a call server that does not know the notes", async () => {
		const { seance, store, sfu } = setup();
		sfu.answers.set("seance:get_state", new Error("seance_unavailable"));
		await seance.refresh();
		expect(store.active).toBe(false);
	});

	it("asks a person who has not answered, with the retention the instance gave", async () => {
		const { seance, store, sfu, calls } = setup();
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		// the instance is asked first, once: the call server is asked only when notes run
		expect(calls).toEqual([["get_seance_state", { meet_room: "room-1" }]]);
		expect(store.isAsked).toBe(true);
		expect(store.retentionDays).toBe(30);
		expect(store.startedBy?.name).toBe("Marc Dupuis");
	});

	it("takes up again, without a card, a yes that was given before (a reload, a return to the call)", async () => {
		const { seance, store, sfu, calls } = setup({
			calls: { get_seance_state: { running: true, you: "agreed", retention_days: 30 } },
		});
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		expect(calls.map(([method]) => method)).toEqual(["get_seance_state", "give_consent"]);
		expect(sfu.sent("seance:consent")).toEqual([{ token: "consent-token" }]);
		expect(store.you).toBe("consented");
		expect(store.isAsked).toBe(false);
	});

	it("leaves alone a person who took their yes back", async () => {
		const { seance, store, sfu, calls } = setup({
			calls: { get_seance_state: { running: true, you: "withdrawn", retention_days: 30 } },
		});
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		expect(store.you).toBe("withdrawn");
		expect(store.isAsked).toBe(false);
		expect(calls.map(([method]) => method)).toEqual(["get_seance_state"]);
		expect(sfu.sent("seance:consent")).toEqual([]);
	});

	it("does not ask again a person who said no in this tab", async () => {
		const { seance, store, sfu, memory } = setup();
		memory.set(`meet-seance-declined:${SEANCE}`, "1");
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		expect(store.you).toBe("declined");
		expect(store.isAsked).toBe(false);
	});

	it("does not ask the instance again about a person who already answered no or took the yes back", async () => {
		for (const you of ["declined", "withdrawn"]) {
			const { seance, store, sfu, calls } = setup({
				calls: { get_seance_state: { running: true, you: "agreed", retention_days: 30 } },
			});
			sfu.answers.set("seance:get_state", view({ you }));
			await seance.refresh();
			expect(store.you).toBe(you);
			expect(calls.map(([method]) => method)).toEqual(["get_seance_state"]); // the first look, no second
			expect(sfu.sent("seance:consent")).toEqual([]);
		}
	});

	it("shows nothing, and takes nothing, when the instance says the notes are over", async () => {
		const { seance, store, sfu } = setup({
			calls: { get_seance_state: { running: false, you: "agreed", retention_days: 30 } },
		});
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		expect(store.active).toBe(false);
		expect(store.isAsked).toBe(false);
		expect(sfu.sent("seance:consent")).toEqual([]);
	});

	it("shows nothing, and asks the call server nothing, where the instance says no notes run or cannot be reached", async () => {
		for (const answer of [{ running: false }, new Error("offline")]) {
			const { seance, store, sfu, calls } = setup({ calls: { get_seance_state: answer } });
			sfu.answers.set("seance:get_state", view());
			await seance.refresh();
			expect(store.active).toBe(false);
			expect(store.isAsked).toBe(false);
			expect(sfu.requests).toEqual([]);
			expect(calls).toHaveLength(1);
		}
	});

	it("asks the person anyway when the notes are announced and the instance cannot be reached then", async () => {
		const { seance, store, sfu } = setup({ calls: { get_seance_state: new Error("offline") } });
		seance.setupSeanceEvents();
		sfu.push("seance:state", {
			active: true,
			seance_id: SEANCE,
			started_at: "2026-10-14T10:00:00.000Z",
			started_by: { id: "host@example.test", name: "Marc Dupuis" },
			capturing: [],
		});
		await vi.waitFor(() => expect(store.isAsked).toBe(true));
		expect(sfu.sent("seance:consent")).toEqual([]); // asked, and nothing is taken without the yes
	});

	it("takes the answer the call server already holds for this person", async () => {
		const { seance, store, sfu, calls } = setup();
		sfu.answers.set("seance:get_state", view({ you: "consented", capturing: [ME] }));
		await seance.refresh();
		expect(store.you).toBe("consented");
		expect(calls.map(([method]) => method)).toEqual(["get_seance_state"]); // captured already: no consent asked
	});
});

describe("useSeance: a person's own answer", () => {
	async function running() {
		const context = setup();
		context.sfu.answers.set("seance:get_state", view());
		await context.seance.refresh();
		context.calls.length = 0;
		context.sfu.requests.length = 0;
		return context;
	}

	it("agreeing records the yes at the instance, then hands the call server its token", async () => {
		const { seance, store, sfu, calls } = await running();
		sfu.answers.set("seance:consent", view({ you: "consented", capturing: [ME] }));
		await seance.agree();
		expect(calls).toEqual([["give_consent", { meeting: SEANCE }]]);
		expect(sfu.sent("seance:consent")).toEqual([{ token: "consent-token" }]);
		expect(store.you).toBe("consented");
		expect(store.isCaptured(ME)).toBe(true);
		expect(store.busy).toBe(false);
	});

	it("a guest agrees with the proof of their lease", async () => {
		const context = setup({ guest: true });
		context.sfu.answers.set("seance:get_state", view());
		await context.seance.refresh();
		context.calls.length = 0;
		await context.seance.agree();
		expect(context.calls).toEqual([
			["give_consent", { meeting: SEANCE, guest_id: ME, guest_session_token: "lease-proof" }],
		]);
	});

	it("a refusal of the instance is told in its own words and nothing is sent to the call server", async () => {
		const { seance, store, sfu, answers, notices } = await running();
		answers.give_consent = instanceError("Nobody is taking notes of this call any more.");
		await seance.agree();
		expect(notices).toEqual([["error", "Nobody is taking notes of this call any more."]]);
		expect(sfu.sent("seance:consent")).toEqual([]);
		expect(store.you).toBe("pending");
		expect(store.busy).toBe(false);
	});

	it("a refusal of the call server is told in our words, not as a code", async () => {
		const { seance, sfu, notices } = await running();
		sfu.answers.set("seance:consent", new Error("e2ee_room"));
		await seance.agree();
		expect(notices).toEqual([["error", "Notes cannot be taken in an end-to-end encrypted meeting."]]);
	});

	it("saying no is remembered in this tab and is not a request to the instance", async () => {
		const { seance, store, sfu, calls, memory } = await running();
		await seance.decline();
		expect(store.you).toBe("declined");
		expect(store.isAsked).toBe(false);
		expect(memory.get(`meet-seance-declined:${SEANCE}`)).toBe("1");
		expect(sfu.sent("seance:decline")).toEqual([{}]);
		expect(calls).toEqual([]);
	});

	it("taking the yes back stops the voice at the call server first, then keeps the record", async () => {
		const { seance, store, sfu, calls } = await running();
		await seance.agree();
		calls.length = 0;
		sfu.requests.length = 0;
		await seance.withdraw(true);
		expect(sfu.sent("seance:withdraw")).toEqual([{ erase: true }]);
		expect(calls).toEqual([["withdraw_consent", { meeting: SEANCE, erase: 1 }]]);
		expect(store.you).toBe("withdrawn");
	});

	it("a call server that is away does not undo the withdrawal at the instance", async () => {
		const { seance, store, sfu, calls } = await running();
		sfu.answers.set("seance:withdraw", new Error("Not connected to SFU"));
		await seance.withdraw(false);
		expect(calls).toEqual([["withdraw_consent", { meeting: SEANCE, erase: 0 }]]);
		expect(store.you).toBe("withdrawn");
	});

	it("a person who withdrew may join the notes again", async () => {
		const { seance, store } = await running();
		await seance.withdraw(false);
		expect(store.you).toBe("withdrawn");
		await seance.agree();
		expect(store.you).toBe("consented");
	});
});

describe("useSeance: the host", () => {
	it("asks the instance, then the call server, then gives the host's own yes", async () => {
		const { seance, store, sfu, calls } = setup();
		sfu.answers.set("seance:start", view({ capturing: [] }));
		sfu.answers.set("seance:consent", view({ you: "consented", capturing: [ME] }));
		await seance.start("Weekly");
		expect(calls.map(([method]) => method)).toEqual(["start_seance", "give_consent", "get_capabilities"]);
		expect(calls[0]).toEqual(["start_seance", { meet_room: "room-1", title: "Weekly" }]);
		expect(sfu.requests.map(([event]) => event)).toEqual(["seance:start", "seance:consent"]);
		expect(sfu.sent("seance:start")).toEqual([{ token: "start-token" }]);
		expect(store.active).toBe(true);
		expect(store.you).toBe("consented");
	});

	it("ends at once, at the instance, a séance the call server refused", async () => {
		const { seance, store, sfu, calls, notices } = setup();
		sfu.answers.set("seance:start", new Error("e2ee_room"));
		await seance.start();
		expect(calls.map(([method]) => method)).toContain("stop_seance");
		expect(calls.find(([method]) => method === "stop_seance")?.[1]).toEqual({ meeting: SEANCE });
		expect(notices).toEqual([["error", "Notes cannot be taken in an end-to-end encrypted meeting."]]);
		expect(store.active).toBe(false);
		expect(store.busy).toBe(false);
	});

	it("tells what the instance refused", async () => {
		const { seance, answers, notices, sfu } = setup();
		answers.start_seance = instanceError("Only the host or a co-host of the call can take notes of it.", 403);
		await seance.start();
		expect(notices).toEqual([["error", "Only the host or a co-host of the call can take notes of it."]]);
		expect(sfu.requests).toEqual([]);
	});

	it("ends the notes at the call server, then at the instance, and says so once", async () => {
		const { seance, store, sfu, calls, notices } = setup();
		sfu.answers.set("seance:get_state", view({ you: "consented", capturing: [ME] }));
		await seance.refresh();
		seance.setupSeanceEvents();
		calls.length = 0;
		sfu.requests.length = 0;
		await seance.stop();
		expect(sfu.sent("seance:stop")).toEqual([{}]);
		expect(calls[0]).toEqual(["stop_seance", { meeting: SEANCE }]);
		expect(store.active).toBe(false);
		// the call server's own announcement, arriving after: nothing more to say
		sfu.push("seance:ended", { seance_id: SEANCE, reason: "stopped" });
		expect(notices.filter(([kind]) => kind !== "error")).toEqual([
			["success", "The notes are over. The minutes will arrive in a few minutes."],
		]);
	});

	it("says the end once to the person who ended the notes, even when the call server announces it first", async () => {
		const { seance, sfu, notices } = setup();
		seance.setupSeanceEvents();
		sfu.answers.set("seance:get_state", view({ you: "consented", capturing: [ME] }));
		await seance.refresh();
		sfu.answers.set("seance:stop", () => {
			sfu.push("seance:ended", { seance_id: SEANCE, reason: "stopped" });
			return { success: true };
		});
		await seance.stop();
		expect(notices.filter(([kind]) => kind !== "error")).toEqual([
			["success", "The notes are over. The minutes will arrive in a few minutes."],
		]);
	});

	it("offers the button only to somebody the instance allows, and not while notes run", async () => {
		const { seance, store, sfu } = setup();
		await seance.loadCapabilities();
		expect(seance.canStart.value).toBe(true);
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		expect(store.active).toBe(true);
		expect(seance.canStart.value).toBe(false);
	});

	it("offers nothing to somebody the instance does not allow, or when the instance does not know the notes", async () => {
		const first = setup({
			calls: { get_capabilities: { enabled: true, can_start: false, reason: "member" } },
		});
		await first.seance.loadCapabilities();
		expect(first.seance.canStart.value).toBe(false);

		const second = setup({ calls: { get_capabilities: instanceError("not found", 404) } });
		await second.seance.loadCapabilities();
		expect(second.store.capabilities).toBeNull();
		expect(second.seance.canStart.value).toBe(false);
	});

	it("never asks the instance for the host's button on behalf of a guest", async () => {
		const { seance, calls, store } = setup({ guest: true });
		await seance.loadCapabilities();
		expect(calls).toEqual([]);
		expect(store.capabilities).toBeNull();
	});
});

describe("useSeance: what the call server pushes", () => {
	it("a person who arrives while notes run is asked, with the same words as everybody", async () => {
		const { seance, store, sfu } = setup();
		seance.setupSeanceEvents();
		sfu.push("seance:state", {
			active: true,
			seance_id: SEANCE,
			started_at: "2026-10-14T10:00:00.000Z",
			started_by: { id: "host@example.test", name: "Marc Dupuis" },
			capturing: ["host@example.test"],
		});
		await vi.waitFor(() => expect(store.isAsked).toBe(true));
		expect(store.capturing).toEqual(["host@example.test"]);
		expect(store.isCaptured("host@example.test")).toBe(true);
		expect(store.isCaptured(ME)).toBe(false);
	});

	it("keeps the list of who is captured up to date", async () => {
		const { seance, store, sfu } = setup();
		seance.setupSeanceEvents();
		sfu.answers.set("seance:get_state", view({ capturing: [] }));
		await seance.refresh();
		sfu.push("seance:state", {
			active: true,
			seance_id: SEANCE,
			started_at: "2026-10-14T10:00:00.000Z",
			started_by: { id: "host@example.test", name: "Marc Dupuis" },
			capturing: ["host@example.test", "paul@example.test"],
		});
		expect(store.capturing).toEqual(["host@example.test", "paul@example.test"]);
	});

	it("tells everybody when the notes end, in words that depend on why", async () => {
		const { seance, store, sfu, notices } = setup();
		seance.setupSeanceEvents();
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		sfu.push("seance:ended", { seance_id: SEANCE, reason: "room_closed" });
		expect(store.active).toBe(false);
		expect(notices).toContainEqual(["info", "The meeting is over, and so are the notes."]);
	});

	it("keeps the notes on screen when a push cannot be read, and ends them when the call server says so", async () => {
		const { seance, store, sfu } = setup();
		seance.setupSeanceEvents();
		sfu.answers.set("seance:get_state", view());
		await seance.refresh();
		sfu.push("seance:state", "garbage");
		sfu.push("seance:state", { active: true });
		expect(store.active).toBe(true);
		sfu.push("seance:state", { active: false });
		expect(store.active).toBe(false);
	});

	it("drops notes the call server announces when the instance says they are over", async () => {
		const { seance, store, sfu, calls } = setup({
			calls: { get_seance_state: { running: false, you: "agreed", retention_days: 30 } },
		});
		seance.setupSeanceEvents();
		sfu.push("seance:state", {
			active: true,
			seance_id: SEANCE,
			started_at: "2026-10-14T10:00:00.000Z",
			started_by: { id: "host@example.test", name: "Marc Dupuis" },
			capturing: [],
		});
		await vi.waitFor(() => expect(calls).toHaveLength(1));
		await vi.waitFor(() => expect(store.active).toBe(false));
		expect(store.isAsked).toBe(false);
		expect(sfu.sent("seance:consent")).toEqual([]);
	});

	it("takes up again, without a card, the person who agreed earlier and sees the notes announced", async () => {
		const { seance, store, sfu } = setup({
			calls: { get_seance_state: { running: true, you: "agreed", retention_days: 30 } },
		});
		seance.setupSeanceEvents();
		sfu.push("seance:state", {
			active: true,
			seance_id: SEANCE,
			started_at: "2026-10-14T10:00:00.000Z",
			started_by: { id: "host@example.test", name: "Marc Dupuis" },
			capturing: ["host@example.test"],
		});
		await vi.waitFor(() => expect(sfu.sent("seance:consent")).toHaveLength(1));
		expect(store.isAsked).toBe(false);
		expect(store.you).toBe("consented");
	});

	it("ignores an end announced when nothing was running and a state it cannot read", () => {
		const { seance, store, sfu, notices } = setup();
		seance.setupSeanceEvents();
		sfu.push("seance:ended", { seance_id: SEANCE, reason: "stopped" });
		sfu.push("seance:state", "garbage");
		sfu.push("seance:state", { active: true });
		expect(store.active).toBe(false);
		expect(notices).toEqual([]);
	});

	it("takes the person again when their track dropped by itself, and not more than once in a while", async () => {
		const { seance, store, sfu } = setup();
		seance.setupSeanceEvents();
		sfu.answers.set("seance:get_state", view({ you: "consented", capturing: [ME] }));
		await seance.refresh();
		sfu.requests.length = 0;
		const dropped = {
			active: true,
			seance_id: SEANCE,
			started_at: "2026-10-14T10:00:00.000Z",
			started_by: { id: "host@example.test", name: "Marc Dupuis" },
			capturing: ["host@example.test"],
		};
		sfu.push("seance:state", dropped);
		await vi.waitFor(() => expect(sfu.sent("seance:consent")).toHaveLength(1));
		sfu.push("seance:state", dropped);
		await Promise.resolve();
		expect(sfu.sent("seance:consent")).toHaveLength(1);
		expect(store.you).toBe("consented");
	});

	it("stops listening when the page goes", async () => {
		const { seance, sfu } = setup();
		seance.setupSeanceEvents();
		expect(sfu.handlers.get("seance:state")?.size).toBe(1);
		seance.dispose();
		expect(sfu.handlers.get("seance:state")?.size ?? 0).toBe(0);
		expect(sfu.handlers.get("seance:ended")?.size ?? 0).toBe(0);
	});
});

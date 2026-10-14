//// Neoffice — added file (no upstream equivalent): the words and the clock of the notes taken of a call.
import { describe, expect, it } from "vitest";
import {
	elapsedLabel,
	retentionSentence,
	seanceEndedMessage,
	seanceErrorMessage,
} from "../seancePresentation";

const START = Date.parse("2026-10-14T10:00:00.000Z");

describe("elapsedLabel", () => {
	it("counts minutes and seconds, and hours after the first one", () => {
		expect(elapsedLabel("2026-10-14T10:00:00.000Z", START)).toBe("00:00");
		expect(elapsedLabel("2026-10-14T10:00:00.000Z", START + 12 * 60_000 + 4_000)).toBe("12:04");
		expect(elapsedLabel("2026-10-14T10:00:00.000Z", START + 3_723_000)).toBe("1:02:03");
	});

	it("never goes below zero when the clock of the page is behind the server's", () => {
		expect(elapsedLabel("2026-10-14T10:00:30.000Z", START)).toBe("00:00");
	});

	it("reads the instance's own format (no zone, a space) as UTC, like the recording clock", () => {
		expect(elapsedLabel("2026-10-14 10:00:00", START + 61_000)).toBe("01:01");
	});

	it("says zero for what it cannot read", () => {
		expect(elapsedLabel(null, START)).toBe("00:00");
		expect(elapsedLabel("garbage", START)).toBe("00:00");
	});
});

describe("the words", () => {
	it("says in a sentence why the call server refused, never a code", () => {
		for (const code of [
			"e2ee_room",
			"seance_unavailable",
			"not_host",
			"already_active",
			"no_active_seance",
			"capacity",
			"rate_limited",
			"token_invalid",
			undefined,
		]) {
			const sentence = seanceErrorMessage(code);
			expect(sentence).toMatch(/\s/);
			if (code) expect(sentence).not.toContain(code);
		}
		expect(seanceErrorMessage("e2ee_room")).toContain("end-to-end");
	});

	it("tells the person who ended the notes when the minutes come, and the others only that it is over", () => {
		expect(seanceEndedMessage("stopped", true)).toContain("minutes will arrive");
		expect(seanceEndedMessage("stopped", false)).not.toContain("minutes");
		expect(seanceEndedMessage("server_restart", false)).toContain("start them again");
		expect(seanceEndedMessage(undefined, false)).toContain("over");
	});

	it("gives the retention as the setting says it, and nothing while it is not known", () => {
		expect(retentionSentence(null)).toBe("");
		expect(retentionSentence(undefined)).toBe("");
		expect(retentionSentence(30)).toContain("30 days");
		expect(retentionSentence(30)).toContain("approved");
		expect(retentionSentence(0)).toContain("kept with the minutes");
	});
});

//// Neoffice — added file (no upstream equivalent): the card that asks each person whether notes may be taken.
import { describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { translationPlugin } from "@/boot/translation";
import SeanceConsentCard from "./SeanceConsentCard.vue";

interface CardProps {
	startedBy?: string | null;
	retentionDays?: number | null;
	busy?: boolean;
}

function mount(props: CardProps = {}) {
	const root = document.createElement("div");
	const agree = vi.fn();
	const decline = vi.fn();
	const app = createApp(SeanceConsentCard, {
		startedBy: "Marc Dupuis",
		retentionDays: 30,
		busy: false,
		onAgree: agree,
		onDecline: decline,
		...props,
	});
	app.use(translationPlugin);
	app.mount(root);
	return { root, app, agree, decline };
}

describe("SeanceConsentCard", () => {
	it("says who is taking notes, what is recorded, and for how long it is kept", () => {
		const { root, app } = mount();
		expect(root.textContent).toContain("Marc Dupuis is taking notes of this meeting");
		expect(root.textContent).toContain("Your voice is recorded while your microphone is on");
		expect(root.querySelector("[data-testid=seance-consent-retention]")?.textContent).toContain("30 days");
		expect(root.textContent).toContain("let them know");
		app.unmount();
	});

	it("is not a recording alert: no red, no REC", () => {
		const { root, app } = mount();
		expect(root.innerHTML).not.toMatch(/red|REC\b/i);
		expect(root.querySelector("section")?.getAttribute("role")).toBe("region");
		app.unmount();
	});

	it("gives yes and no the same weight, and neither is chosen for the person", () => {
		const { root, app } = mount();
		const yes = root.querySelector("[data-testid=seance-agree]") as HTMLElement;
		const no = root.querySelector("[data-testid=seance-decline]") as HTMLElement;
		expect(yes.getAttribute("variant")).toBe(no.getAttribute("variant"));
		expect(yes.getAttribute("size")).toBe(no.getAttribute("size"));
		expect(yes.getAttribute("label")).toBe("I agree");
		expect(no.getAttribute("label")).toBe("Not for me");
		app.unmount();
	});

	it("answers with what the person pressed, and only that", () => {
		const first = mount();
		(first.root.querySelector("[data-testid=seance-agree]") as HTMLElement).click();
		expect(first.agree).toHaveBeenCalledOnce();
		expect(first.decline).not.toHaveBeenCalled();
		first.app.unmount();

		const second = mount();
		(second.root.querySelector("[data-testid=seance-decline]") as HTMLElement).click();
		expect(second.decline).toHaveBeenCalledOnce();
		expect(second.agree).not.toHaveBeenCalled();
		second.app.unmount();
	});

	it("says nothing about retention while the instance has not said, and names the host when unknown", () => {
		const { root, app } = mount({ startedBy: null, retentionDays: null });
		expect(root.querySelector("[data-testid=seance-consent-retention]")).toBeNull();
		expect(root.querySelector("[data-testid=seance-consent-title]")?.textContent).toContain(
			"Notes are being taken of this meeting",
		);
		app.unmount();
	});

	it("explains who sees the minutes and how to take the yes back, on request", async () => {
		const { root, app } = mount();
		expect(root.querySelector("[data-testid=seance-more-text]")).toBeNull();
		(root.querySelector("[data-testid=seance-more]") as HTMLElement).click();
		await nextTick();
		const text = root.querySelector("[data-testid=seance-more-text]")?.textContent ?? "";
		expect(text).toContain("Who sees the minutes?");
		expect(text).toContain("Marc Dupuis chooses");
		expect(text).toContain("take your agreement back at any time");
		app.unmount();
	});
});

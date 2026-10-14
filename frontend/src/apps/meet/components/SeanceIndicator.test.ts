//// Neoffice — added file (no upstream equivalent): the pill of the header while notes are being taken.
import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { translationPlugin } from "@/boot/translation";
import SeanceIndicator from "./SeanceIndicator.vue";

const mounted: Array<{ unmount: () => void }> = [];

interface PillProps {
	startedAt?: string | null;
	you?: "pending" | "consented" | "declined" | "withdrawn";
	canEnd?: boolean;
	busy?: boolean;
}

function mount(props: PillProps = {}) {
	const root = document.createElement("div");
	document.body.appendChild(root);
	const agree = vi.fn();
	const withdraw = vi.fn();
	const end = vi.fn();
	const app = createApp(SeanceIndicator, {
		startedAt: new Date(Date.now() - 125_000).toISOString(),
		you: "consented",
		canEnd: false,
		busy: false,
		onAgree: agree,
		onWithdraw: withdraw,
		onEnd: end,
		...props,
	});
	app.use(translationPlugin);
	app.mount(root);
	mounted.push({
		unmount: () => {
			app.unmount();
			root.remove();
		},
	});
	return { root, agree, withdraw, end };
}

async function open(root: HTMLElement) {
	(root.querySelector("[data-testid=seance-pill]") as HTMLElement).click();
	await nextTick();
}

afterEach(() => {
	for (const item of mounted.splice(0)) item.unmount();
});

describe("SeanceIndicator", () => {
	it("shows a calm pill with the clock, for everybody", () => {
		const { root } = mount();
		const pill = root.querySelector("[data-testid=seance-pill]") as HTMLElement;
		expect(pill.textContent).toContain("Notes");
		expect(root.querySelector("[data-testid=seance-clock]")?.textContent).toBe("02:05");
		expect(pill.innerHTML).not.toMatch(/red/i);
	});

	it("tells a person who agreed what is recorded, and lets them take it back", async () => {
		const { root, withdraw } = mount({ you: "consented" });
		await open(root);
		expect(document.body.querySelector("[data-testid=seance-status]")?.textContent).toContain("You agreed");
		(document.body.querySelector("[data-testid=seance-withdraw]") as HTMLElement).click();
		expect(withdraw).toHaveBeenCalledWith(false);
		await open(root);
		(document.body.querySelector("[data-testid=seance-erase]") as HTMLElement).click();
		expect(withdraw).toHaveBeenLastCalledWith(true);
	});

	it("tells a person who is not recorded so, and lets them join", async () => {
		for (const you of ["declined", "withdrawn"] as const) {
			const { root, agree } = mount({ you });
			await open(root);
			expect(document.body.querySelector("[data-testid=seance-status]")?.textContent).toContain("not being recorded");
			expect(document.body.querySelector("[data-testid=seance-withdraw]")).toBeNull();
			(document.body.querySelector("[data-testid=seance-join]") as HTMLElement).click();
			expect(agree).toHaveBeenCalledOnce();
		}
	});

	it("offers to end the notes to the host and to nobody else", async () => {
		const host = mount({ canEnd: true });
		await open(host.root);
		(document.body.querySelector("[data-testid=seance-end]") as HTMLElement).click();
		expect(host.end).toHaveBeenCalledOnce();

		const guest = mount({ canEnd: false });
		await open(guest.root);
		expect(document.body.querySelector("[data-testid=seance-end]")).toBeNull();
	});

	it("hangs its menu outside the header: the header of Meet clips what falls below it", async () => {
		const { root } = mount();
		await open(root);
		const menu = document.body.querySelector("[data-testid=seance-menu]") as HTMLElement;
		expect(menu).not.toBeNull();
		expect(root.contains(menu)).toBe(false);
		expect(menu.style.top).not.toBe("");
		expect(menu.className).toContain("fixed");
	});

	it("closes when the person clicks away or presses escape", async () => {
		const { root } = mount();
		await open(root);
		expect(document.body.querySelector("[data-testid=seance-menu]")).not.toBeNull();
		document.body.click();
		await nextTick();
		expect(document.body.querySelector("[data-testid=seance-menu]")).toBeNull();

		await open(root);
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
		await nextTick();
		expect(document.body.querySelector("[data-testid=seance-menu]")).toBeNull();
	});
});

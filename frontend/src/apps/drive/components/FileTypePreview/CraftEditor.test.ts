//// Neoffice — added file (no upstream equivalent): where the Drive page stores what a Craft editor saves (CraftEditor.vue).
//// An imported document (.xls, .csv, .doc…) is never written: its first save is a new file next to it, a save the editor
//// hands over before the page has moved to that file goes into it, and the page then opens it.
import { createApp, nextTick } from "vue"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import CraftEditor from "./CraftEditor.vue"

const { routerPush, call, toast } = vi.hoisted(() => ({
	routerPush: vi.fn(),
	call: vi.fn(),
	toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("frappe-ui", async () => {
	const { defineComponent, h } = await import("vue")
	return {
		Button: defineComponent({ setup: (_props, { slots }) => () => h("button", slots.default?.()) }),
		Dialog: defineComponent({ render: () => null }),
		call,
		toast,
	}
})
vi.mock("vue-router", () => ({
	useRouter: () => ({ push: routerPush }),
	onBeforeRouteLeave: () => {},
	onBeforeRouteUpdate: () => {},
}))
vi.mock("@/apps/drive/utils/craftNora", () => ({ offerNora: () => () => {} }))

// What the page was told for an imported workbook (get_craft_editor_config with `imports`).
const imported = {
	available: true,
	editor: "sheet",
	base_url: "/assets/suite/craft/gridcraft/",
	version: "0.19.1",
	file_name: "Budget.xls",
	can_write: true,
	access_token: "read-only-token",
	access_token_ttl: 3600,
	wopi_src: "/wopi/files/original-id",
	imported: true,
	save_as: "Budget.xlsx",
}

let requests: { url: string; method: string }[] = []
let posted: Record<string, unknown>[] = []
let releaseImport: () => void = () => {}
// What a write into the new file answers.
let wopiStatus = 200

function answer(body: unknown, status = 200) {
	return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })
}

beforeEach(() => {
	requests = []
	posted = []
	wopiStatus = 200
	vi.stubGlobal(
		"fetch",
		vi.fn(async (url: string, init: RequestInit = {}) => {
			requests.push({ url, method: init.method || "GET" })
			if (url.includes("save_import")) {
				// held until the test lets it through: a second save is handed over meanwhile
				await new Promise<void>((resolve) => (releaseImport = resolve))
				return answer({ message: { file_id: "new-id", file_name: "Budget.xlsx" } })
			}
			if (url.startsWith("/wopi/files/new-id/contents")) return new Response("", { status: wopiStatus })
			throw new Error(`unexpected request ${init.method} ${url}`)
		})
	)
	call.mockResolvedValue({
		available: true,
		can_write: true,
		wopi_src: "/wopi/files/new-id",
		access_token: "token-of-the-new-file",
	})
})

afterEach(() => {
	vi.unstubAllGlobals()
	vi.clearAllMocks()
	document.body.innerHTML = ""
})

async function mount(config = imported) {
	const root = document.createElement("div")
	document.body.appendChild(root)
	const app = createApp(CraftEditor, { config, previewEntity: { name: "original-id" } })
	app.config.globalProperties.__ = (text: string, args?: unknown[]) =>
		args ? text.replace(/\{(\d+)\}/g, (_, i) => String(args[Number(i)])) : text
	app.mount(root)
	await nextTick()
	const frame = root.querySelector("iframe") as HTMLIFrameElement
	vi.spyOn(frame.contentWindow as Window, "postMessage").mockImplementation((message: unknown) => {
		posted.push(message as Record<string, unknown>)
	})
	return { app, frame }
}

// The editor in the frame hands a file over, as its bridge does.
function editorSaves(frame: HTMLIFrameElement, name: string, saveAs?: boolean) {
	window.dispatchEvent(
		new MessageEvent("message", {
			data: { type: "gridcraft:save", name, bytes: new TextEncoder().encode("PK\u0003\u0004 workbook").buffer, saveAs },
			origin: window.location.origin,
			source: frame.contentWindow,
		})
	)
}

const settle = async () => {
	for (let i = 0; i < 20; i++) await new Promise((resolve) => setTimeout(resolve, 0))
}

describe("a save of an imported document", () => {
	it("is a new file next to it; a second save handed over meanwhile goes into that file, never into a second one", async () => {
		const { app, frame } = await mount()
		editorSaves(frame, "Budget (imported).xlsx")
		editorSaves(frame, "Budget (imported).xlsx")
		await settle()
		releaseImport()
		await settle()

		// one new file, the second save written in place into it with its own token, the original never written
		expect(requests.filter((r) => r.url.includes("save_import"))).toHaveLength(1)
		expect(call).toHaveBeenCalledWith("suite.drive.wopi.craft.get_craft_editor_config", { file_id: "new-id" })
		expect(requests.filter((r) => r.url.startsWith("/wopi/files/new-id/contents") && r.method === "POST")).toHaveLength(1)
		expect(requests.some((r) => r.url.startsWith("/wopi/files/original-id") && r.method === "POST")).toBe(false)
		// the page then opens the new file, once
		expect(routerPush).toHaveBeenCalledTimes(1)
		expect(routerPush).toHaveBeenCalledWith({ name: "drive-File", params: { entityName: "new-id" } })
		expect(posted.filter((m) => m.type === "gridcraft:saved").map((m) => m.ok)).toEqual([true, true])
		app.unmount()
	})

	it("keeps the page when the save handed over meanwhile could not be written, and the next one goes into the new file", async () => {
		const { app, frame } = await mount()
		wopiStatus = 500
		editorSaves(frame, "Budget (imported).xlsx")
		editorSaves(frame, "Budget (imported).xlsx")
		await settle()
		releaseImport()
		await settle()
		expect(routerPush).not.toHaveBeenCalled()
		expect(posted.filter((m) => m.type === "gridcraft:saved").map((m) => m.ok)).toEqual([true, false])
		expect(toast.error).toHaveBeenCalled()

		wopiStatus = 200
		editorSaves(frame, "Budget (imported).xlsx")
		await settle()
		expect(requests.filter((r) => r.url.includes("save_import"))).toHaveLength(1)
		expect(requests.filter((r) => r.url.startsWith("/wopi/files/new-id/contents"))).toHaveLength(2)
		expect(routerPush).toHaveBeenCalledTimes(1)
		expect(routerPush).toHaveBeenCalledWith({ name: "drive-File", params: { entityName: "new-id" } })
		app.unmount()
	})

	it("says so, and offers the file, when the editor could not open what the page sent it", async () => {
		const warn = vi.spyOn(console, "warn").mockImplementation(() => {})
		const { app, frame } = await mount({ ...imported, editor: "word", file_name: "Rapport.doc", save_as: "Rapport.docx" })
		window.dispatchEvent(
			new MessageEvent("message", {
				data: { type: "wordcraft:openFailed", name: "Rapport.doc", error: "not a Word document" },
				origin: window.location.origin,
				source: frame.contentWindow,
			})
		)
		await settle()
		const page = document.body.textContent || ""
		expect(page).toContain("The editor could not open this document. You can download it.")
		expect([...document.querySelectorAll("button")].some((b) => b.textContent?.includes("Download"))).toBe(true)
		expect(warn).toHaveBeenCalled()
		// what the editor then holds is its own empty document: a save of it writes nothing
		window.dispatchEvent(
			new MessageEvent("message", {
				data: { type: "wordcraft:save", name: "Rapport.docx", bytes: new ArrayBuffer(4), saveAs: true },
				origin: window.location.origin,
				source: frame.contentWindow,
			})
		)
		await settle()
		expect(requests).toEqual([])
		expect(posted.find((m) => m.type === "wordcraft:saved")?.ok).toBe(false)
		warn.mockRestore()
		app.unmount()
	})

	it("of an .odt in its own type under its own name is refused, and nothing is written", async () => {
		const { app, frame } = await mount({ ...imported, editor: "word", file_name: "Lettre.odt", save_as: "Lettre.docx" })
		window.dispatchEvent(
			new MessageEvent("message", {
				data: { type: "wordcraft:save", name: "Lettre.odt", bytes: new ArrayBuffer(4), saveAs: false },
				origin: window.location.origin,
				source: frame.contentWindow,
			})
		)
		await settle()
		expect(requests).toEqual([])
		const saved = posted.find((m) => m.type === "wordcraft:saved")
		expect(saved?.ok).toBe(false)
		expect(String(saved?.error)).toContain("Lettre.docx")
		expect(routerPush).not.toHaveBeenCalled()
		app.unmount()
	})
})

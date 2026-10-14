//// Neoffice — added file (no upstream equivalent). What the Office preview does with each answer of the server
//// about the document's editor. "Download" on it did nothing once: upstream assigns `window.location.ref` (a typo)
//// to the link it encodes for Microsoft's viewer, and a user whose editor did not start was left with no way to get
//// the document (05.10.2026). Collabora is gone since (maintenance#1570): the answers are the Craft editors'.
import { createApp, nextTick } from "vue"
import { afterEach, describe, expect, it, vi } from "vitest"

import MSOfficePreview from "./MSOfficePreview.vue"

const { entitiesDownload, server } = vi.hoisted(() => ({
	entitiesDownload: vi.fn(),
	// What the next call of `get_craft_editor_config` does.
	server: { answer: null as unknown, fails: false },
}))

vi.mock("frappe-ui", async (importOriginal) => ({
	...(await importOriginal<Record<string, unknown>>()),
	createResource: (options: { onSuccess: (data: unknown) => void; onError: () => void }) => ({
		submit: () => (server.fails ? options.onError() : options.onSuccess(server.answer)),
	}),
}))
vi.mock("@/apps/drive/utils/download.js", () => ({ entitiesDownload }))
vi.mock("@/apps/drive/components/FileTypePreview/CraftEditor.vue", async () => {
	const { h } = await import("vue")
	return {
		default: {
			props: ["config"],
			render() {
				return h("div", { "data-editor": (this as unknown as { config: { editor: string } }).config.editor })
			},
		},
	}
})

const entity = { name: "a-file-id", title: "sheet.xlsx", file_type: "Spreadsheet" }

async function open(answer: unknown, fails = false) {
	server.answer = answer
	server.fails = fails
	const root = document.createElement("div")
	document.body.appendChild(root)
	const app = createApp(MSOfficePreview, { previewEntity: entity })
	app.config.globalProperties.__ = (text: string) => text
	app.mount(root)
	await nextTick()
	return { root, app }
}

const button = (root: HTMLElement, label: string) =>
	[...root.querySelectorAll("button")].find((candidate) => candidate.textContent?.trim() === label)

afterEach(() => {
	vi.restoreAllMocks()
	entitiesDownload.mockClear()
	document.body.innerHTML = ""
})

describe("the Office preview", () => {
	it("frames the editor the server names, and nothing else", async () => {
		const { root, app } = await open({ available: true, editor: "sheet", file_name: "sheet.xlsx" })
		expect(root.querySelector("[data-editor='sheet']"), root.innerHTML).toBeTruthy()
		expect(root.querySelector("iframe")).toBeNull()
		expect(button(root, "Download")).toBeUndefined()
		app.unmount()
	})

	it("downloads the document from the editor-unavailable card when the site has no build of the editor", async () => {
		const { root, app } = await open({
			available: false,
			editor: "sheet",
			reason: "The editor is not installed on this site",
		})
		expect(root.textContent).toContain("Your document has not left this server.")
		const download = button(root, "Download")
		expect(download, root.innerHTML).toBeTruthy()
		download?.click()

		expect(entitiesDownload).toHaveBeenCalledWith([entity])
		app.unmount()
	})

	it("says the editor is unavailable, and offers the file, when the question itself fails", async () => {
		const { root, app } = await open(null, true)
		expect(root.textContent).toContain("The editor is unavailable")
		expect(button(root, "Try again")).toBeTruthy()
		expect(button(root, "Download")).toBeTruthy()
		app.unmount()
	})

	it("sends a type no editor opens nowhere before the person has agreed", async () => {
		const fetchSpy = vi.spyOn(globalThis, "fetch")
		const { root, app } = await open({ available: false, reason: "File type not supported" })
		expect(root.textContent).toContain("Are you sure you want to preview?")
		expect(root.querySelector("iframe"), "no viewer is framed before the click").toBeNull()
		expect(fetchSpy).not.toHaveBeenCalled()
		expect(button(root, "View anyway")).toBeTruthy()
		expect(button(root, "Download")).toBeTruthy()
		app.unmount()
	})
})

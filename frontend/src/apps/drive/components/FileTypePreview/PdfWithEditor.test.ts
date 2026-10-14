//// Neoffice — added file (no upstream equivalent). A PDF opens in the PDF editor directly, as the other documents do
//// (14.10.2026): nothing to click first, and upstream's preview only where the site has no build of the editor.
import { createApp, nextTick } from "vue"
import { afterEach, describe, expect, it, vi } from "vitest"

import PdfWithEditor from "./PdfWithEditor.vue"

const { server, asked } = vi.hoisted(() => ({
	// What the next call of `get_craft_editor_config` does, and what it was asked.
	server: { answer: null as unknown, fails: false },
	asked: [] as unknown[],
}))

vi.mock("frappe-ui", async (importOriginal) => ({
	...(await importOriginal<Record<string, unknown>>()),
	createResource: (options: { onSuccess: (data: unknown) => void; onError: () => void }) => ({
		submit: (params: unknown) => {
			asked.push(params)
			return server.fails ? options.onError() : options.onSuccess(server.answer)
		},
	}),
}))
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
vi.mock("@/apps/drive/components/FileTypePreview/PDFPreview.vue", async () => {
	const { h } = await import("vue")
	return { default: { render: () => h("div", { "data-preview": "pdf" }) } }
})

const entity = { name: "a-file-id", title: "scan.pdf", file_type: "PDF", write: 1 }

async function open(answer: unknown, fails = false) {
	server.answer = answer
	server.fails = fails
	asked.length = 0
	const root = document.createElement("div")
	document.body.appendChild(root)
	const app = createApp(PdfWithEditor, { previewEntity: entity })
	app.config.globalProperties.__ = (text: string) => text
	app.mount(root)
	await nextTick()
	return { root, app }
}

afterEach(() => {
	document.body.innerHTML = ""
})

describe("the PDF preview", () => {
	it("opens the PDF in the PDF editor directly, with no button in front of it", async () => {
		const { root, app } = await open({ available: true, editor: "pdf", file_name: "scan.pdf" })
		expect(root.querySelector("[data-editor='pdf']"), root.innerHTML).toBeTruthy()
		expect(root.querySelector("[data-preview]"), "the preview is not drawn first").toBeNull()
		expect(root.textContent).not.toContain("Edit PDF")
		expect(root.querySelector("button")).toBeNull()
		expect(asked).toEqual([{ file_id: "a-file-id", requested: "pdf" }])
		app.unmount()
	})

	it("opens it in the editor for a person who may only read it too, as the other documents do", async () => {
		const readOnly = { name: "a-file-id", title: "scan.pdf", file_type: "PDF", write: 0 }
		server.answer = { available: true, editor: "pdf", can_write: false }
		const root = document.createElement("div")
		document.body.appendChild(root)
		const app = createApp(PdfWithEditor, { previewEntity: readOnly })
		app.mount(root)
		await nextTick()
		expect(root.querySelector("[data-editor='pdf']")).toBeTruthy()
		app.unmount()
	})

	it("previews the PDF as upstream does when this site has no build of the PDF editor", async () => {
		const { root, app } = await open({ available: false, editor: "pdf", reason: "The editor is not installed on this site" })
		expect(root.querySelector("[data-preview='pdf']")).toBeTruthy()
		expect(root.querySelector("[data-editor]")).toBeNull()
		app.unmount()
	})

	it("previews the PDF as upstream does when the question itself fails", async () => {
		const { root, app } = await open(null, true)
		expect(root.querySelector("[data-preview='pdf']")).toBeTruthy()
		expect(root.querySelector("[data-editor]")).toBeNull()
		app.unmount()
	})
})

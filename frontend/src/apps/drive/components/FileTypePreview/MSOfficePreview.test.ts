//// Neoffice — added file (no upstream equivalent). "Download" on the Office preview did nothing: upstream
//// assigns `window.location.ref` (a typo) to the link it encodes for Microsoft's viewer. A user whose editor
//// did not start was left with no way to get the document (05.10.2026).
import { createApp, nextTick } from "vue"
import { describe, expect, it, vi } from "vitest"

import MSOfficePreview from "./MSOfficePreview.vue"

const { entitiesDownload } = vi.hoisted(() => ({ entitiesDownload: vi.fn() }))

vi.mock("frappe-ui", async (importOriginal) => ({
	...(await importOriginal<Record<string, unknown>>()),
	// The editor pre-flight answers: Collabora is deployed here, and it did not come up.
	createResource: (options: { onSuccess: (data: unknown) => void }) => ({
		submit: () => options.onSuccess({ can_edit: false, wopi_enabled: true, retryable: false }),
	}),
}))
vi.mock("@/apps/drive/utils/download.js", () => ({ entitiesDownload }))
vi.mock("@/apps/drive/components/FileTypePreview/CollaboraEditor.vue", () => ({ default: { render: () => null } }))

describe("the Office preview when the editor did not start", () => {
	it("downloads the document from the editor-unavailable card", async () => {
		const root = document.createElement("div")
		document.body.appendChild(root)
		const entity = { name: "a-file-id", title: "sheet.xlsx", file_type: "Spreadsheet" }
		const app = createApp(MSOfficePreview, { previewEntity: entity })
		app.config.globalProperties.__ = (text: string) => text
		app.mount(root)
		await nextTick()

		const download = [...root.querySelectorAll("button")].find((button) => button.textContent?.trim() === "Download")
		expect(download, root.innerHTML).toBeTruthy()
		download?.click()

		expect(entitiesDownload).toHaveBeenCalledWith([entity])
		app.unmount()
	})
})

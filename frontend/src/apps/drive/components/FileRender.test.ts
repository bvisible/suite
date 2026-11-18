//// Neoffice — added file (no upstream equivalent): which preview the file page mounts for a type a Craft editor imports.
//// A .csv may be "Text" to the Drive and a .tsv, .xlsb or .rtf has no type it previews: they are asked of the editors first
//// (MSOfficePreview.vue), and shown as before when no editor of the site takes them.
import { createApp, defineComponent, h, nextTick } from "vue"
import { afterEach, describe, expect, it, vi } from "vitest"

import FileRender from "./FileRender.vue"

const { editors } = vi.hoisted(() => ({
	// Whether the stand-in of the Office preview finds an editor for the file.
	editors: { open: true },
}))

// files.js reaches the drive's toasts, which read frappe-ui's toast at load: the test stub of frappe-ui has none
// (as opensInEditor.test.ts, neoffice-maintenance#2366)
vi.mock("@/apps/drive/utils/toasts", () => ({ toast: () => {} }))
vi.mock("@/apps/drive/resources/permissions", () => ({
	diskSettings: { data: { preview_size: 100 }, fetch: () => {} },
}))
// `__esModule`: the page loads its previews with defineAsyncComponent, which takes `default` of a module only
vi.mock("@/apps/drive/components/FileTypePreview/MSOfficePreview.vue", () => ({
	__esModule: true,
	default: defineComponent({
		props: { previewEntity: Object, handsBack: Boolean },
		emits: ["no-editor"],
		mounted() {
			if (!editors.open) this.$emit("no-editor")
		},
		render() {
			return h("div", { "data-preview": "office", "data-hands-back": String(this.handsBack) })
		},
	}),
}))
vi.mock("@/apps/drive/components/FileTypePreview/TextPreview.vue", () => ({
	__esModule: true,
	default: defineComponent({ render: () => h("div", { "data-preview": "text" }) }),
}))

async function render(entity: Record<string, unknown>) {
	const root = document.createElement("div")
	document.body.appendChild(root)
	const app = createApp(FileRender, { previewEntity: { name: "a-file-id", file_size: 10, ...entity } })
	app.config.globalProperties.__ = (text: string) => text
	app.mount(root)
	// the previews are async components: let them load, then let the stand-in say what it found
	for (let i = 0; i < 10; i++) {
		await new Promise((resolve) => setTimeout(resolve, 0))
		await nextTick()
	}
	return { root, app }
}

const shown = (root: HTMLElement) => root.querySelector("[data-preview]")?.getAttribute("data-preview")

afterEach(() => {
	editors.open = true
	document.body.innerHTML = ""
})

describe("the preview of a type an editor imports", () => {
	// The file page's entity carries no mime type (get_entity_with_permissions): only its name and the Drive's type.
	it("asks the editors first for a .csv the Drive filed as text", async () => {
		const { root, app } = await render({ file_name: "export.csv", file_type: "Text" })
		expect(shown(root), root.innerHTML).toBe("office")
		expect(root.querySelector("[data-hands-back]")?.getAttribute("data-hands-back")).toBe("true")
		app.unmount()
	})

	it("shows that .csv as text when no editor of the site takes it", async () => {
		editors.open = false
		const { root, app } = await render({ file_name: "export.csv", file_type: "Text" })
		expect(shown(root), root.innerHTML).toBe("text")
		app.unmount()
	})

	it("asks the editors for a type the Drive previews not at all, and says it cannot preview it when none takes it", async () => {
		const { root, app } = await render({ file_name: "book.xlsb", file_type: "Unknown" })
		expect(shown(root), root.innerHTML).toBe("office")
		app.unmount()
		editors.open = false
		const again = await render({ file_name: "letter.rtf", file_type: "Unknown" })
		expect(shown(again.root)).toBeUndefined()
		expect(again.root.textContent).toContain("Previews are not supported for this file type")
		again.app.unmount()
	})

	it("leaves an .xls in the Office preview, which keeps its own viewer when no editor takes it", async () => {
		editors.open = false
		const { root, app } = await render({ file_name: "old.xls", file_type: "Spreadsheet" })
		expect(shown(root), root.innerHTML).toBe("office")
		expect(root.querySelector("[data-hands-back]")?.getAttribute("data-hands-back")).toBe("false")
		app.unmount()
	})

	it("shows a .csv or .tsv filed as a spreadsheet as text, never the outside viewer, when no editor takes it", async () => {
		const first = await render({ file_name: "export.csv", file_type: "Spreadsheet" })
		expect(shown(first.root), first.root.innerHTML).toBe("office")
		expect(first.root.querySelector("[data-hands-back]")?.getAttribute("data-hands-back")).toBe("true")
		first.app.unmount()
		editors.open = false
		for (const entity of [
			{ file_name: "export.csv", file_type: "Spreadsheet" },
			{ file_name: "export.tsv", file_type: "Unknown" },
		]) {
			const { root, app } = await render(entity)
			expect(shown(root), root.innerHTML).toBe("text")
			app.unmount()
		}
	})
})

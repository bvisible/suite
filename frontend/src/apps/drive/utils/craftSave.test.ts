//// Neoffice — added file (no upstream equivalent): where a file a Craft editor hands the Drive page goes (craftSave.js).
import { describe, expect, it } from "vitest"
import { savedUnderItsOwnName, saveTarget } from "@/apps/drive/utils/craftSave"

const native = { editor: "sheet", file_name: "Budget.xlsx" }
const sheetImport = { editor: "sheet", file_name: "Export.csv", imported: true, save_as: "Export.xlsx" }
const workbookImport = { editor: "sheet", file_name: "Budget.xls", imported: true, save_as: "Budget.xlsx" }
const odt = { editor: "word", file_name: "Lettre.odt", imported: true, save_as: "Lettre.docx" }
const doc = { editor: "word", file_name: "Lettre.doc", imported: true, save_as: "Lettre.docx" }

describe("where a save goes", () => {
	it("writes a native document in place, and makes a copy for Save As or another name of its type", () => {
		expect(saveTarget(native, "Budget.xlsx")).toBe("overwrite")
		expect(saveTarget(native, "BUDGET.XLSX")).toBe("overwrite")
		expect(saveTarget(native, "Budget.xlsx", true)).toBe("copy")
		expect(saveTarget(native, "Budget 2.xlsx")).toBe("copy")
		expect(saveTarget(native, "Budget.pdf")).toBe("export")
	})

	it("never writes an import: its save in the editor's type is a new file, whatever name the editor gives it", () => {
		// GridCraft: `<stem> (imported).xlsx` for a workbook it imports, `<stem>.xlsx` for a CSV
		expect(saveTarget(workbookImport, "Budget (imported).xlsx")).toBe("import")
		expect(saveTarget(sheetImport, "Export.xlsx")).toBe("import")
		// WordCraft: an imported .doc saves as `<stem>.docx`, with Save As set
		expect(saveTarget(doc, "Lettre.docx", true)).toBe("import")
		expect(saveTarget(odt, "Lettre.docx", true)).toBe("import")
	})

	it("keeps an .odt or .rtf WordCraft saves in its own type, and downloads what is an export", () => {
		expect(saveTarget(odt, "Lettre.odt")).toBe("kept")
		expect(saveTarget(odt, "Lettre.pdf")).toBe("export")
		// GridCraft's CSV of a CSV bears the original's name: an export the person asked for, never written over it
		expect(saveTarget(sheetImport, "Export.csv")).toBe("export")
		expect(saveTarget(workbookImport, "Budget (imported).pdf")).toBe("export")
	})
})

describe("savedUnderItsOwnName", () => {
	const session = (file_name: string, editor = "word") => ({ editor, file_name, imported: true, save_as: "x" })
	it("is NeoDoc's .odt and .rtf, not its .doc, not another editor's import, not a document it writes in place", () => {
		expect(savedUnderItsOwnName(session("Note.odt"))).toBe(true)
		expect(savedUnderItsOwnName(session("NOTE.RTF"))).toBe(true)
		expect(savedUnderItsOwnName(session("Note.doc"))).toBe(false)
		expect(savedUnderItsOwnName(session("Budget.ods", "sheet"))).toBe(false)
		expect(savedUnderItsOwnName({ editor: "word", file_name: "Note.odt" })).toBe(false)
	})
})

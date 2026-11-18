//// Neoffice — added file (no upstream equivalent): which files the file page gives the whole frame (File.vue).
import { describe, expect, it, vi } from "vitest"
import { importsInEditor, opensInEditor } from "@/apps/drive/utils/files"

// files.ts reaches the drive's toasts, which read frappe-ui's toast at load: the test stub of frappe-ui has none
// (neoffice-maintenance#2366)
vi.mock("@/apps/drive/utils/toasts", () => ({ toast: () => {} }))

describe("opensInEditor", () => {
  it("is true for an Office file and for a PDF, by type or by name", () => {
    expect(opensInEditor({ mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", file_name: "a.docx" })).toBe(true)
    expect(opensInEditor({ mime_type: "application/pdf", file_name: "a" })).toBe(true)
    expect(opensInEditor({ title: "Facture.PDF" })).toBe(true)
  })

  it("is false for a folder, an image and nothing", () => {
    expect(opensInEditor({ is_folder: 1, title: "x.pdf" })).toBe(false)
    expect(opensInEditor({ mime_type: "image/png", file_name: "a.png" })).toBe(false)
    expect(opensInEditor(null)).toBe(false)
  })

  it("is true for a type an editor imports, which the Drive files as text or under no type it previews", () => {
    for (const file_name of ["export.csv", "export.TSV", "book.xlsb", "letter.rtf", "old.xls", "old.doc", "a.odt", "a.ods"]) {
      expect(opensInEditor({ file_name }), file_name).toBe(true)
      expect(importsInEditor({ file_name }), file_name).toBe(true)
    }
    expect(importsInEditor({ title: "export.csv" })).toBe(true)
  })

  it("does not take a native type, another type, or a folder for an import", () => {
    for (const file_name of ["a.docx", "a.xlsx", "a.pptx", "a.pdf", "a.txt", "a.ppt", "csv"]) {
      expect(importsInEditor({ file_name }), file_name).toBe(false)
    }
    expect(importsInEditor({ is_folder: 1, file_name: "export.csv" })).toBe(false)
    expect(importsInEditor(null)).toBe(false)
  })
})

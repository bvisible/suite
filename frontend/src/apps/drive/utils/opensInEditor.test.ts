//// Neoffice — added file (no upstream equivalent): which files the file page gives the whole frame (File.vue).
import { describe, expect, it, vi } from "vitest"
import { opensInEditor } from "@/apps/drive/utils/files"

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
})

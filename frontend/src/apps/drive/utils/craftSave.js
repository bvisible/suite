//// Neoffice — added file (no upstream equivalent): where a file a Craft editor hands the Drive page goes (CraftEditor.vue).

export const extensionOf = (name) => {
  const text = String(name || '')
  return text.includes('.') ? text.split('.').pop().toLowerCase() : ''
}

const same = (a, b) => String(a || '').toLowerCase() === String(b || '').toLowerCase()

/**
 * The imports NeoWrite writes back in their own type under their own name when it is not told they are imports (an .odt,
 * an .rtf; its Save of a .doc comes back as a .docx): the page says to use Save As unless the editor can make the .docx on
 * Save (`savesImports` of its `ready`, CraftEditor.vue).
 */
export const savedUnderItsOwnName = (session) =>
  !!session.imported && session.editor === 'word' && ['odt', 'rtf'].includes(extensionOf(session.file_name))

/**
 * What the page does with `name`, a file the editor saved. `session`: what get_craft_editor_config answered (`editor`,
 * `file_name`, and `imported` with `save_as` for a type the editor imports); `saveAs`: the editor said Save As.
 *
 * - `import`: an imported document (.xls, .csv, .doc…) saved in the editor's own type: a new file next to the
 *   original (save_import), which is never written;
 * - `kept`: an imported document that NeoWrite saves in its own type under its own name (the Save of an .odt or an
 *   .rtf by a build that does not make the .docx): nothing is written, the original stays as it was, and the person is
 *   told to use Save As, which comes back in the editor's type;
 * - `copy`: Save As, or another name of the document's type: a new file next to it (save_copy);
 * - `overwrite`: the document itself, in place (WOPI);
 * - `export`: anything else (a PDF, a picture, a CSV of the sheet): the browser downloads it.
 */
export function saveTarget(session, name, saveAs = false) {
  if (session.imported) {
    if (extensionOf(name) === extensionOf(session.save_as)) return 'import'
    // GridCraft's export of a .csv as CSV bears the original's name too: that one is an export.
    if (session.editor === 'word' && same(name, session.file_name)) return 'kept'
    return 'export'
  }
  // PdfCraft says when the user asked for Save As (it keeps the document's name); the others carry the new name.
  if (saveAs) return 'copy'
  if (same(name, session.file_name)) return 'overwrite'
  if (extensionOf(name) === extensionOf(session.file_name)) return 'copy'
  return 'export'
}

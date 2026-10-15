// //// Neoffice — added file (no upstream equivalent): the Vite side of neoffice-i18n-core.mjs, which says what the
// //// text of Sheets, Slides, Writer and the Drive's pages is and how it goes through __() (maintenance#1592). The
// //// files of those apps stay upstream's, byte for byte: they are read here as Vite loads them, before the Vue
// //// plugin splits them, so a merge brings no conflict and no marker, and the new text of an upstream release is
// //// said in the reader's language from the first build. What the build asks the catalogue for is listed by
// //// scripts/gen-i18n-registry.mjs in src/neoffice/i18nRegistry.ts; src/test/neoffice-i18n.test.ts fails when that
// //// list is stale, and when a rewrite would not parse.
import type { Plugin } from 'vite'

// @ts-ignore plain JS: shared with scripts/gen-i18n-registry.mjs, which node runs without a build
import { isInScope, transformSource } from './neoffice-i18n-core.mjs'

export function neofficeI18n(): Plugin {
  return {
    name: 'neoffice-i18n',
    enforce: 'pre',
    transform(code, id) {
      // the SFC itself, before the Vue plugin splits it: its ?vue&type=… parts are already compiled
      if (id.includes('?')) return null
      if (!isInScope(id)) return null
      let result
      try {
        result = transformSource(code, id)
      } catch (error) {
        this.error(`neoffice-i18n could not read ${id}: ${String(error)}`)
        return null
      }
      if (!result.changed) return null
      return { code: result.code, map: null }
    },
  }
}

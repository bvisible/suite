//// Neoffice — added file (no upstream equivalent): pins neoffice-i18n-core.mjs, the reading of upstream's English
//// apps that puts their text through __() at build (maintenance#1592).
import fs from 'node:fs'
import path from 'node:path'

import * as sfc from '@vue/compiler-sfc'
import ts from 'typescript'
import { describe, expect, it } from 'vitest'

// @ts-ignore the module is plain JS next to vite.config.ts, shared with scripts/gen-i18n-registry.mjs
import { collectMessages, isInScope, isText, scopedFiles, transformSource } from '../../neoffice-i18n-core.mjs'
import { registrySource } from '../../scripts/gen-i18n-registry-source.mjs'

const root = path.resolve(__dirname, '../..')
const FILE = path.join(root, 'src/apps/sheets/components/Fixture.vue')

// compileScript resolves the types of defineProps<…>() through the file system
sfc.registerTS(() => ts)
const fsApi = {
  fileExists: (f: string) => fs.existsSync(f),
  readFile: (f: string) => fs.readFileSync(f, 'utf8'),
  realpath: (f: string) => fs.realpathSync(f),
}

function transform(source: string, file = FILE) {
  return transformSource(source, file) as { code: string; messages: string[]; left: { text: string }[] }
}

describe('what a person reads', () => {
  it('says a text node, a run of text and values, and the words of an attribute', () => {
    const { code, messages } = transform(`<template>
  <div>
    <Button label="Save" variant="solid" />
    <p>No sheets yet</p>
    <span>Showing {{ count }} of {{ total }}</span>
    <input placeholder="Search sheets…" />
  </div>
</template>`)
    expect(code).toContain(`:label="__('Save')"`)
    expect(code).toContain(`{{ __('No sheets yet') }}`)
    expect(code).toContain(`{{ __('Showing {0} of {1}', [count, total]) }}`)
    expect(code).toContain(`:placeholder="__('Search sheets…')"`)
    expect(code).toContain('variant="solid"')
    expect(messages).toEqual(['Save', 'No sheets yet', 'Showing {0} of {1}', 'Search sheets…'])
  })

  it('says the choice of a text binding and the label of an object, not a comparison or a class', () => {
    const { code } = transform(`<template>
  <Button :label="locked ? 'Unlock' : 'Lock'" :class="active ? 'bg-surface-gray-2 text-ink' : ''" @click="mode === 'Edit' && go()" />
  <Dropdown :options="[{ label: 'Rename', onClick: rename }]" />
</template>`)
    expect(code).toContain(`:label="locked ? __('Unlock') : __('Lock')"`)
    expect(code).toContain(`'bg-surface-gray-2 text-ink'`)
    expect(code).toContain(`mode === 'Edit'`)
    expect(code).toContain(`{ label: __('Rename'), onClick: rename }`)
  })

  it('makes an object of a script read the language when it is used, and says toasts', () => {
    const { code, messages } = transform(
      `export const FORMATS = [{ label: 'Percent', value: 'percent' }]
export function done() {
  toast.success('Saved')
  console.error('Load failed:', 1)
  const o = { description: \`Deleted \${name}\` }
}`,
      path.join(root, 'src/apps/sheets/engine/x.js'),
    )
    expect(code).toContain(`{ get label() { return typeof __ === 'function' ? __('Percent') : 'Percent' }, value: 'percent' }`)
    expect(code).toContain(`toast.success(__('Saved'))`)
    expect(code).toContain(`console.error('Load failed:', 1)`)
    expect(code).toContain(
      `get description() { return typeof __ === 'function' ? __('Deleted {0}', [name]) : \`Deleted \${name}\` }`,
    )
    expect(messages.sort()).toEqual(['Deleted {0}', 'Percent', 'Saved'])
  })

  it('gives the text as written when it is read before the catalogue is loaded', () => {
    // vue-router copies a route's `meta` when it is installed, before boot/translation.ts has set window.__: a getter that
    // called __ bare threw « __ is not defined » there and the whole Suite stayed blank (osiris, 15.10)
    const { code } = transform(
      `const menu = { label: 'Open', hint: \`Deleted \${name}\` }\nmenu`,
      path.join(root, 'src/apps/sheets/engine/x.js'),
    )
    const run = (name: string) => new Function('name', `${code}\nreturn menu`)(name) as { label: string; hint: string }
    const host = globalThis as unknown as { __?: unknown }
    const before = host.__
    try {
      delete host.__
      const early = run('A')
      expect(early.label).toBe('Open')
      expect(early.hint).toBe('Deleted A')
      host.__ = (message: string, replace?: string[]) =>
        `fr:${message}`.replace(/{(\d+)}/g, (_m, i) => String((replace ?? [])[Number(i)]))
      const late = run('B')
      expect(late.label).toBe('fr:Open')
      expect(late.hint).toBe('fr:Deleted B')
    } finally {
      if (before === undefined) delete host.__
      else host.__ = before
    }
  })

  it('leaves what is not text alone', () => {
    for (const value of ['asc', 'row', 'lucide-lock', 'rrggbb', 'bg-surface-gray-2 px-2', 'Inter', 'USD ($)', 'SUM', '15 Jan 2025', '/api/method/x', 'a.png', '[Attachment: {0}]'])
      expect(isText(value), value).toBe(false)
    for (const value of ['Bold', 'Move to Trash', '{0} of {1}', 'Can view', 'Loading…'])
      expect(isText(value), value).toBe(true)
  })

  it('does not touch a file outside the four apps, or text already said', () => {
    const { code } = transform(`<template><p>{{ __('Hello world') }}</p><Button :label="__('Save')" /></template>`)
    expect(code).toContain(`{{ __('Hello world') }}`)
    expect(code).not.toContain(`__(__(`)
  })
})

describe('the apps as they are', () => {
  it('lists every message of the build in src/neoffice/i18nRegistry.ts', { timeout: 120_000 }, () => {
    const { messages } = collectMessages(root)
    const registry = fs.readFileSync(path.join(root, 'src/neoffice/i18nRegistry.ts'), 'utf8')
    expect(registry, 'run node scripts/gen-i18n-registry.mjs').toBe(registrySource(messages))
  })

  it('still parses and compiles after the rewrite, in every file that is read', { timeout: 120_000 }, () => {
    const broken: string[] = []
    for (const file of scopedFiles(root)) {
      const source = fs.readFileSync(file, 'utf8')
      const { code } = transformSource(source, file) as { code: string }
      if (code === source) continue
      const rel = path.relative(root, file)
      if (file.endsWith('.vue')) {
        const { descriptor, errors } = sfc.parse(code, { filename: file })
        if (errors.length) broken.push(`${rel}: ${String(errors[0])}`)
        if (descriptor.template) {
          const out = sfc.compileTemplate({ source: descriptor.template.content, filename: file, id: 'x' })
          if (out.errors.length) broken.push(`${rel}: template ${String(out.errors[0])}`)
        }
        for (const block of [descriptor.script, descriptor.scriptSetup]) {
          if (!block) continue
          const out = ts.transpileModule(block.content, { reportDiagnostics: true, compilerOptions: { target: ts.ScriptTarget.ESNext } })
          const bad = (out.diagnostics ?? []).find((d) => d.category === ts.DiagnosticCategory.Error)
          if (bad) broken.push(`${rel}: script ${ts.flattenDiagnosticMessageText(bad.messageText, ' ')}`)
        }
        // what Vue makes of it: a getter in withDefaults() has to be a getter of the prop's default, not a failure
        if (descriptor.script || descriptor.scriptSetup) {
          try {
            sfc.compileScript(descriptor, { id: 'x', inlineTemplate: true, fs: fsApi })
          } catch (error) {
            broken.push(`${rel}: compileScript ${String(error).slice(0, 140)}`)
          }
        }
      } else {
        const out = ts.transpileModule(code, { reportDiagnostics: true, fileName: file, compilerOptions: { target: ts.ScriptTarget.ESNext } })
        const bad = (out.diagnostics ?? []).find((d) => d.category === ts.DiagnosticCategory.Error)
        if (bad) broken.push(`${rel}: ${ts.flattenDiagnosticMessageText(bad.messageText, ' ')}`)
      }
    }
    expect(broken).toEqual([])
  })
})

describe("frappe-ui's editor", () => {
  const lib = path.join(root, 'node_modules/frappe-ui/src')

  it('reads the files of the editor that were looked at, and no other', () => {
    expect(isInScope(`${lib}/molecules/editor/commands.ts`)).toBe(true)
    expect(isInScope(`${lib}/molecules/editor/extensions/link/LinkEditorPopup.vue`)).toBe(true)
    // the title stored in the document is not a label
    expect(isInScope(`${lib}/molecules/editor/extensions/toc-node/toc-node-extension.ts`)).toBe(false)
    // the components of the library that were looked at are read, the others are not
    expect(isInScope(`${lib}/components/Dialog/Dialog.vue`)).toBe(true)
    expect(isInScope(`${lib}/components/Badge/Badge.vue`)).toBe(false)
    // the submodule of the repository: a src/components of its own, next to frontend/
    expect(isInScope('/work/suite/frappe-ui/src/components/Badge/Badge.vue')).toBe(false)
    expect(isInScope('/work/suite/frappe-ui/src/components/Dialog/Dialog.vue')).toBe(true)
    expect(isInScope('/work/suite/frappe-ui/src/utils/call.ts')).toBe(false)
    expect(isInScope('/x/frappe-ui/experimental/TextEditor/commands.js')).toBe(true)
    // the experimental calendar is said by neoffice-calendar-i18n.ts, not here
    expect(isInScope('/x/frappe-ui/experimental/Calendar/Calendar.vue')).toBe(false)
    // the helper of the confirmation dialogs is read: its defaults say « Cancel »
    expect(isInScope(`${lib}/utils/dialog.ts`)).toBe(true)
    expect(isInScope(`${lib}/utils/call.ts`)).toBe(false)
    // as pnpm lays them out
    expect(isInScope('/x/node_modules/.pnpm/frappe-ui@1/node_modules/frappe-ui/src/molecules/editor/menu.ts')).toBe(true)
  })

  it('says the label of a command when it is shown, not when the module loads', () => {
    const { code, messages } = transformSource(
      `export const commandMeta = {\n  bold: {\n    label: 'Bold',\n    icon: 'lucide-bold',\n  },\n}\n`,
      `${lib}/molecules/editor/commands.ts`,
    ) as { code: string; messages: string[] }
    expect(code).toContain(`get label() { return typeof __ === 'function' ? __('Bold') : 'Bold' },`)
    expect(messages).toEqual(['Bold'])
  })

  it('gives every app a file mounts on its own the __ of the page', () => {
    // a pop-up made with createApp() does not inherit the page's app: __ in its template would throw at render
    const missing: string[] = []
    for (const file of scopedFiles(root)) {
      const source = fs.readFileSync(file, 'utf8')
      if (!/\bcreateApp\(/.test(source)) continue
      // `changed` is what the plugin goes by: a file whose only rewrite is an override must count as changed
      const { code, changed } = transformSource(source, file) as { code: string; changed: boolean }
      if (!changed || !code.includes('globalProperties.__')) missing.push(path.relative(root, file))
    }
    expect(missing).toEqual([])
  })

  it('reads the commands of the real menu lazily, and says the table commands', () => {
    const file = path.join(root, 'node_modules/frappe-ui/src/molecules/editor/menu.ts')
    if (!fs.existsSync(file)) return
    const { code, messages } = transformSource(fs.readFileSync(file, 'utf8'), file) as { code: string; messages: string[] }
    expect(code).toContain('get label() { return meta.label },')
    expect(code).toContain(`get label() { return typeof __ === 'function' ? __(label) : label },`)
    expect(messages).toEqual(expect.arrayContaining(['Insert column left', 'Delete table', 'Merge cells', 'Split cell']))
  })
})

describe('what is read of the suite itself', () => {
  it('reads the shell, Mail, Meet and Calendar, and nothing that runs in a worker or is our own', () => {
    for (const f of ['src/shell/LauncherView.vue', 'src/apps/mail/components/Modals/SettingsModal.vue', 'src/apps/meet/pages/Home.vue',
      'src/apps/calendar/pages/CalendarView.vue', 'src/utils/confirmLeave.ts', 'src/router/index.ts', 'src/apps/registry.ts'])
      expect(isInScope(path.join(root, f)), f).toBe(true)
    for (const f of ['src/apps/mail/sw.ts', 'src/apps/meet/utils/media/e2eeTransformWorker.ts', 'src/neoffice/i18nRegistry.ts',
      'src/boot/translation.ts', 'src/test/translation-setup.ts', 'src/apps/slides/service-worker.js'])
      expect(isInScope(path.join(root, f)), f).toBe(false)
  })
})

describe('what an override says', () => {
  it('names a message with a context, and the registry writes it as the catalogue keys it', () => {
    expect(registrySource(['Empty\u0004Trash', 'Save'])).toContain(`__('Empty', null, 'Trash')`)
    expect(registrySource(['Empty\u0004Trash', 'Save'])).toContain(`__('Save')`)
    const file = path.join(root, 'src/apps/drive/components/Navbar.vue')
    const { code, messages } = transformSource(fs.readFileSync(file, 'utf8'), file) as { code: string; messages: string[] }
    expect(code).toContain(`label: __('Empty', null, 'Trash'),`)
    expect(messages).toContain('Empty\u0004Trash')
  })

  it('says every occurrence of a text it is asked to say everywhere', () => {
    const file = path.join(root, 'src/apps/drive/ui/drive/components/MoveDialog.vue')
    const { code } = transformSource(fs.readFileSync(file, 'utf8'), file) as { code: string }
    expect(code).not.toContain(`file_name: 'Home'`)
    expect(code).not.toContain(`file_name: 'Site'`)
    expect(code.match(/get file_name\(\) \{ return __\('Home'\) \}/g)).toHaveLength(3)
    expect(code.match(/get file_name\(\) \{ return __\('Site'\) \}/g)).toHaveLength(1)
  })

  it('says what a function of an object returns when its key is one of the returning keys', () => {
    const { code } = transform(
      `export const items = [{ getLabel: (editor) => (editor.can() ? 'Merge cells' : 'Split cell'), defaultLabel: 'Heading' }]`,
      path.join(root, 'src/apps/writer/components/x.js'),
    )
    expect(code).toContain(`__('Merge cells')`)
    expect(code).toContain(`__('Split cell')`)
    expect(code).toContain(`get defaultLabel() { return typeof __ === 'function' ? __('Heading') : 'Heading' }`)
  })
})

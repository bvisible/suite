// //// Neoffice — added file (no upstream equivalent): puts the text a person reads through __() in the apps that
// //// upstream wrote in English only (Sheets, Slides, Writer, the Drive's own pages), without touching their files
// //// (maintenance#1592).
// ////
// //// Upstream's Sheets, Slides and Writer, and a good part of the Drive, never call __(): « Cancel », « Move to
// //// Trash », « Bold » are literals in templates, and menus, dialogs and toasts are English objects. Editing every
// //// file would put a marker on each of a thousand lines and a conflict on each at the next merge. This module is the
// //// whole of the change instead: it reads a source file the way a translator would (Vue template text, the label,
// //// title, placeholder… attributes, the label/title/description/message… values of objects, the first argument of
// //// toast calls) and says what to rewrite. It is used twice, by the Vite plugin (neoffice-i18n.ts) at build, and by
// //// scripts/gen-i18n-registry.mjs, which lists every message in src/neoffice/i18nRegistry.ts so that the catalogue
// //// extractor of the translations finds them (the sources of the apps no longer name them).
// ////
// //// What is rewritten, and why that much and no more:
// ////  * Template: a text node (or a run of text and {{ }} with no element in it, which becomes one message with
// ////    {0}, {1}… for the interpolations); a static label/title/placeholder/… attribute (made a binding);
// ////    the string literals of an interpolation, of a binding of such an attribute, and the label/title/…
// ////    values of an object in any binding; the first argument of a toast.
// ////  * Script: a label/title/description/message/… value of an object becomes a getter (`get label() { return
// ////    __('Bold') }`), so a list built when the module loads still reads the language the translations came in; the
// ////    first argument of toast calls. Never console.*, never a comparison operand, never a string that is not text
// ////    (a class list, an identifier, a path, a font, a currency code: see isText).
// ////  * A template literal with ${} becomes __('… {0} …', [x]).
// ////
// //// A text next to an element inside one sentence (« … see <a>the docs</a> for details ») is left alone: it cannot be
// //// translated in pieces. neoffice-i18n.ts lists what it left, for a person to take by hand.
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const sfc = require('@vue/compiler-sfc')
const ts = require('typescript')

/** The apps this module reads. Anything else is somebody's own, already written with __(). */
export const SCOPE = /[\\/]src[\\/]apps[\\/](sheets|slides|writer|drive)[\\/]/
export const isInScope = (file) => SCOPE.test(file) && /\.(vue|js|ts)$/.test(file) && !/\.(test|spec)\.|\.d\.ts$/.test(file)

/** Attributes of a template whose value a person reads. */
const ATTRS = new Set([
  'label', 'title', 'placeholder', 'description', 'aria-label', 'alt', 'tooltip', 'text', 'message', 'subtitle',
  'confirm-label', 'cancel-label', 'header', 'hint', 'empty-text', 'no-results-text', 'helper-text',
])
/** Keys of an object whose string value a person reads. */
const KEYS = new Set([
  'title', 'label', 'message', 'description', 'placeholder', 'text', 'tooltip', 'subtitle', 'hint', 'header',
  'emptyText', 'confirmLabel', 'cancelLabel', 'successMessage', 'errorMessage', 'loadingMessage', 'toastMessage',
])
/**
 * Functions whose returned literals are only ever shown (checked one by one: a function that returns a name the code
 * looks up again — recencyBucket in Sheets — must not be here), and the keys of an object whose value is such a function.
 */
const DISPLAY_FUNCTIONS = new Set([
  'formatDate', 'commentTime', '_fillSummary', 'cfRuleLabel', 'dayLabel', 'entityLabel', 'itemString',
  '_validateName', '_validateRange',
])
const RETURNING_KEYS = new Set(['validate', 'success', 'error', 'loading'])
const SKIP_TAGS = new Set(['script', 'style', 'code', 'pre', 'kbd', 'svg', 'textarea'])
const TOAST_OBJECTS = new Set(['toast', 'nToast', 'toaster'])
const TOAST_FUNCTIONS = new Set(['toast', 'raiseToast', 'showToast', 'notify'])
const TOAST_METHODS = new Set(['error', 'success', 'warning', 'info', 'message', 'loading'])

/** Strings that look like text but are not: fonts, units, formats, formula names, codes. */
const NOT_TEXT = new Set([
  'px', 'pt', 'em', 'rem', 'ms', 'fps', 'dpi', 'MB', 'KB', 'GB', 'OK', 'ID', 'URL', 'PDF', 'DOCX', 'XLSX', 'CSV',
  'JSON', 'HTML', 'SUM', 'COUNT', 'AVERAGE', 'MIN', 'MAX', 'COUNTA', 'Inter', 'Caveat', 'Comic Sans', 'Comfortaa',
  'EB Garamond', 'Fantasy', 'Geist', 'IBM Plex Sans', 'JetBrains Mono', 'Lora', 'Merriweather', 'Nunito',
  'DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD', 'FontOptions', 'Robin', 'Hood', 'Microsoft',
])

/**
 * (file, message) pairs that are data the code compares with or stores, not words a person only reads.
 * Found by looking, for every message, for a literal comparison with it (maintenance#1592); keep the reason.
 */
const KEEP = [
  // the default label of a new tab is stored in the document, and tabs.ts tells an untouched tab by it
  [/writer[\\/]components[\\/]ToC\.vue$/, 'Untitled'],
  // the old sidebar tells its two spaces apart by their label
  [/drive[\\/]components[\\/]Sidebar\.vue$/, 'Home'],
  [/drive[\\/]components[\\/]Sidebar\.vue$/, 'Trash'],
]
const isKept = (file, message) => KEEP.some(([re, m]) => re.test(file) && m === message)

/**
 * Sentences that a template breaks around an element (« Sharing "<div>{{ name }}</div>" »): they cannot be told in
 * pieces, so each is rewritten here, from the exact upstream text, as one message with its value in it. A file
 * that no longer contains the text is a build error (neoffice-i18n.ts): the sentence moved, say it again.
 */
const OVERRIDES = [
  {
    file: /drive[\\/]ui[\\/]drive[\\/]components[\\/]MoveDialog\.vue$/,
    find: '            Moving "\n            <div class="truncate max-w-[80%]">\n              {{ props.entities[0].file_name }}\n            </div>\n            "\n',
    replace: '            <div class="truncate max-w-[100%]">\n              {{ __(\'Moving "{0}"\', [props.entities[0].file_name]) }}\n            </div>\n',
    messages: ['Moving "{0}"'],
  },
  {
    file: /drive[\\/]ui[\\/]drive[\\/]components[\\/]ShareDialog\.vue$/,
    find: '          Sharing "\n          <div class="truncate min-w-0">\n            {{ file?.file_name }}\n          </div>\n          "\n',
    replace: '          <div class="truncate min-w-0">\n            {{ __(\'Sharing "{0}"\', [file?.file_name]) }}\n          </div>\n',
    messages: ['Sharing "{0}"'],
  },
  {
    file: /drive[\\/]components[\\/]FileTypePreview[\\/]MSOfficePreview\.vue$/,
    find: "        This preview is generated by an external service (<b>Microsoft</b>), not by Drive. For extra\n        privacy, we'd suggest downloading.\n",
    replace: "        {{ __('This preview is generated by an external service (Microsoft), not by Drive. For extra privacy, we\\'d suggest downloading.') }}\n",
    messages: ["This preview is generated by an external service (Microsoft), not by Drive. For extra privacy, we'd suggest downloading."],
  },
  {
    file: /drive[\\/]components[\\/]FileTypePreview[\\/]MSOfficePreview\.vue$/,
    find: '      Please ask your site\'s administrator to set the access key in the\n      <a href="/app/drive-disk-settings" class="underline">Settings</a>.\n',
    replace: '      {{ __(\'Please ask your site\\\'s administrator to set the access key in the Drive disk settings.\') }}\n      <a href="/app/drive-disk-settings" class="underline">{{ __(\'Settings\') }}</a>\n',
    messages: ["Please ask your site's administrator to set the access key in the Drive disk settings.", 'Settings'],
  },
  {
    file: /sheets[\\/]pages[\\/]Home\.vue$/,
    find: '          "<strong>{{ deleteTarget?.title }}</strong>" will be moved to Trash. You\n          can restore it from there before it\'s permanently deleted.\n',
    replace: '          {{ __(\'"{0}" will be moved to Trash. You can restore it from there before it\\\'s permanently deleted.\', [deleteTarget?.title]) }}\n',
    messages: ['"{0}" will be moved to Trash. You can restore it from there before it\'s permanently deleted.'],
  },
  {
    file: /sheets[\\/]pages[\\/]Trash\.vue$/,
    find: '          "<strong>{{ purgeTarget?.title }}</strong>" and its full history will be\n          <strong>permanently deleted</strong>. This can\'t be undone.\n',
    replace: '          {{ __(\'"{0}" and its full history will be permanently deleted. This can\\\'t be undone.\', [purgeTarget?.title]) }}\n',
    messages: ['"{0}" and its full history will be permanently deleted. This can\'t be undone.'],
  },
]


// The names of the groups of a list are the keys of an object, shown as headings: the heading says it through
// __(group), and the names the code builds are listed here so that the registry (and the catalogue) has them.
const GROUPS_OF_TIME = ['Today', 'Yesterday', 'Last seven days', 'Earlier this week', 'Earlier this month', 'Earlier this year', 'Earlier', 'Older than a year']
OVERRIDES.push(
  {
    file: /writer[\\/]components[\\/]RoundedListView\.vue$/,
    find: '        <h2 class="text-sm font-medium text-ink-gray-5">\n          {{ group }}\n',
    replace: '        <h2 class="text-sm font-medium text-ink-gray-5">\n          {{ __(group) }}\n',
    messages: GROUPS_OF_TIME,
  },
  {
    file: /drive[\\/]components[\\/]ListView\.vue$/,
    find: ':key="group.group" :label="group.group"',
    replace: ':key="group.group" :label="__(group.group)"',
    messages: GROUPS_OF_TIME,
  },
  {
    // the bucket of a sheet by its date: the names stay what the code looks up, only what the list shows is said
    file: /sheets[\\/]utils[\\/]recency-groups\.js$/,
    find: '      group: g,\n      collapsed: collapsedByLabel.get(g) ?? false,\n',
    replace: '      group: __(g),\n      collapsed: collapsedByLabel.get(__(g)) ?? false,\n',
    messages: ['Today', 'Previous 7 days', 'Previous 30 days', 'Earlier'],
  },
)

const WORDS = /\p{L}{2,}/u

/** Whether a string is a sentence, a word or a phrase a person reads (and not an identifier, a class list, a path). */
export function isText(text) {
  // {0}, {1}: the places a value goes. They count as a word when the text has words besides (« {0} of {1} »).
  const holes = /\{\d+\}/.test(text)
  const bare = text.replace(/\{\d+\}/g, ' ').trim()
  const t = holes ? text.replace(/\{\d+\}/g, 'N').trim() : text.trim()
  if (!t || t.length < 2 || !WORDS.test(bare)) return false
  if (NOT_TEXT.has(bare) || NOT_TEXT.has(t)) return false
  if (/^\d/.test(t) && !holes) return false // « 15 Jan 2025 », « 3:30 PM »: examples of a format, not words
  if (/^[A-Z]{2,5}( \(.{1,3}\))?$/.test(bare)) return false // « USD ($) », « PDF »: codes
  if (/^(https?:|\/|\.\/|#|@|mailto:|data:)/.test(t)) return false
  if (/^\[.*\]$/.test(t)) return false // « [Attachment: x] »: the content of an exported document
  if (/^[\w.-]+\.(png|svg|jpe?g|gif|webp|json|css|js|ts|vue|html|txt|csv)$/i.test(t)) return false
  if (/\$\{|\{\{|<%/.test(t)) return false
  // one token without a space: a word (« Bold », « Cancel ») only when it begins with a capital; « asc », « row »,
  // « bold », « lucide-lock », « rrggbb » are values
  if (!/\s/.test(t)) {
    if (!/^[A-Z\u00C0-\u00DD]/.test(t)) return false
    if (/[_\-\[\]\/\\=:;()]/.test(t.slice(1)) && !/^[A-Z][a-z]+(…|\.\.\.|:)?$/.test(t)) return false
    if (/^[A-Z0-9_]+$/.test(t) && t.length > 5) return false // CONSTANT_NAMES, MIN_WIDTH
  }
  // a class list: tokens with a dash/bracket/colon and no capital in them
  if (/(^|\s)[a-z0-9]+(-[a-z0-9!\[\]\/.%#()]+)+(\s|$)/.test(t) && !/[A-Z]/.test(t)) return false
  if (/(^|\s)(\w+:)?[\w-]+-\[[^\]]+\]/.test(t)) return false
  return true
}

const collapse = (s) => s.replace(/\s+/g, ' ').trim()

/** `'…'` for a message, with what a single-quoted JS string needs escaped. */
export function jsString(message) {
  return `'${message.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n')}'`
}

const callTranslate = (message, args) => `__(${jsString(message)}${args && args.length ? `, [${args.join(', ')}]` : ''})`
const htmlAttr = (code) => code.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')

/** An edit: [start, end) of the source becomes `text`; `message` is what it asks the catalogue for. */
function edit(start, end, text, message, why, nested = []) {
  return { start, end, text, message, why, nested }
}

/**
 * A value spliced into a message (`${x ? 'its original location' : 'their original locations'}`) is said too:
 * a French sentence must not end on an English phrase. Returns the source of the value and what it asks for.
 */
function sayNested(code, filename) {
  const found = expressionEdits(code, 0, 'text', filename)
  if (!found.length) return { code, messages: [] }
  const kept = settle(found)
  let out = code
  for (const e of [...kept].reverse()) out = out.slice(0, e.start) + e.text + out.slice(e.end)
  return { code: out, messages: kept.flatMap((e) => [e.message, ...(e.nested ?? [])]) }
}

/** The call for a message, keeping the spaces the literal began and ended with (« 'These items ' + next text »). */
function callKeepingSpaces(raw, message, args) {
  const lead = raw.match(/^\s+/)?.[0] ?? ''
  const trail = raw.match(/\s+$/)?.[0] ?? ''
  const call = callTranslate(message, args)
  if (!lead && !trail) return call
  const space = (x) => jsString(x.replace(/\s+/g, ' '))
  return `(${lead ? `${space(lead)} + ` : ''}${call}${trail ? ` + ${space(trail)}` : ''})`
}

// ------------------------------------------------------------------------------------------------ expressions

/**
 * The edits of one expression (the source of a binding, an interpolation or a script).
 * `offset` is where the expression's first character sits in the file; `mode`:
 *   'script'  — a key/value of an object becomes a getter; toast calls
 *   'binding' — only what is displayed: object values and toast calls
 *   'text'    — an interpolation or the binding of an attribute that is text: also bare string literals
 */
export function expressionEdits(code, offset, mode, filename = 'x.ts', wrapped = 1) {
  const kind = filename.endsWith('.js') ? ts.ScriptKind.JS : ts.ScriptKind.TS
  const source = wrapped ? `(${code})` : code
  const shift = wrapped ? 1 : 0
  const sf = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, kind)
  const edits = []
  const isInsideTranslate = (n) => {
    for (let p = n.parent; p; p = p.parent) {
      if (ts.isCallExpression(p) && ts.isIdentifier(p.expression) && ['__', 't', 'translate'].includes(p.expression.text)) return true
    }
    return false
  }
  // A literal is shown as it is when nothing but a choice stands between it and the whole expression:
  // `cond ? 'A' : 'B'`, `a || 'None'`. As an argument (a date format, a key, a unit) it is not text.
  const isDisplayed = (n) => {
    let child = n
    for (let p = n.parent; p; child = p, p = p.parent) {
      if (ts.isParenthesizedExpression(p) || ts.isAsExpression(p) || ts.isNonNullExpression(p)) continue
      if (ts.isConditionalExpression(p)) {
        if (p.condition === child) return false
        continue
      }
      if (ts.isBinaryExpression(p) && ['||', '??', '&&'].includes(p.operatorToken.getText(sf))) {
        if (p.operatorToken.getText(sf) === '&&' && p.left === child) return false
        if (p.left === child && p.operatorToken.getText(sf) !== '&&') continue
        continue
      }
      return ts.isSourceFile(p) || ts.isExpressionStatement(p) && ts.isSourceFile(p.parent)
    }
    return false
  }
  const at = (n) => [offset + n.getStart(sf) - shift, offset + n.getEnd() - shift]
  const srcOf = (n) => source.slice(n.getStart(sf), n.getEnd())

  // the message of a literal / template literal, with the sources of its ${} parts
  const messageOf = (n) => {
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) return { message: n.text, args: [] }
    if (ts.isTemplateExpression(n)) {
      let message = n.head.text
      const args = []
      n.templateSpans.forEach((span, i) => {
        message += `{${i}}${span.literal.text}`
        args.push(srcOf(span.expression))
      })
      return { message, args }
    }
    return null
  }
  const usable = (m) => m && isText(m.message) && !/\n/.test(m.message.trim())

  const wrap = (n, why) => {
    const m = messageOf(n)
    if (!usable(m)) return null
    const [s, e] = at(n)
    const nested = []
    const args = m.args.map((a) => {
      const r = sayNested(a, filename)
      nested.push(...r.messages)
      return r.code
    })
    return edit(s, e, callKeepingSpaces(m.message, collapse(m.message), args), collapse(m.message), why, nested)
  }

  // the string literals a function returns (its expression body, or its return statements, not nested functions')
  const literalsOf = (e) => {
    if (ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e) || ts.isTemplateExpression(e)) return [e]
    if (ts.isParenthesizedExpression(e)) return literalsOf(e.expression)
    if (ts.isConditionalExpression(e)) return [...literalsOf(e.whenTrue), ...literalsOf(e.whenFalse)]
    if (ts.isBinaryExpression(e) && ['||', '??'].includes(e.operatorToken.getText(sf))) return [...literalsOf(e.left), ...literalsOf(e.right)]
    return []
  }
  const returnedLiterals = (fn) => {
    const out = []
    if (ts.isArrowFunction(fn) && !ts.isBlock(fn.body)) return literalsOf(fn.body)
    const walk = (n) => {
      if (n !== fn && (ts.isFunctionLike(n))) return
      if (ts.isReturnStatement(n) && n.expression) out.push(...literalsOf(n.expression))
      ts.forEachChild(n, walk)
    }
    walk(fn)
    return out
  }
  const isFunctionNode = (n) => n && (ts.isArrowFunction(n) || ts.isFunctionExpression(n))
  const sayReturned = (fn, why) => {
    for (const lit of returnedLiterals(fn)) {
      const e = wrap(lit, why)
      if (e && !edits.some((x) => x.start <= e.start && e.end <= x.end)) edits.push(e)
    }
  }

  const visit = (n) => {
    if (mode === 'script') {
      if (ts.isFunctionDeclaration(n) && n.name && DISPLAY_FUNCTIONS.has(n.name.text)) sayReturned(n, `returns:${n.name.text}`)
      else if (ts.isMethodDeclaration(n) && n.name && DISPLAY_FUNCTIONS.has(n.name.getText(sf))) sayReturned(n, 'returns')
      else if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && DISPLAY_FUNCTIONS.has(n.name.text) && isFunctionNode(n.initializer)) {
        sayReturned(n.initializer, `returns:${n.name.text}`)
      } else if (ts.isPropertyAssignment(n) && (ts.isIdentifier(n.name) || ts.isStringLiteral(n.name)) &&
          RETURNING_KEYS.has(n.name.text) && isFunctionNode(n.initializer)) {
        sayReturned(n.initializer, `returns:${n.name.text}`)
      }
    }
    if (ts.isCallExpression(n)) {
      const callee = n.expression
      if (ts.isIdentifier(callee) && ['__', 't', 'translate'].includes(callee.text)) return // already said
      let isToast = false
      if (ts.isIdentifier(callee) && TOAST_FUNCTIONS.has(callee.text)) isToast = true
      if (ts.isPropertyAccessExpression(callee) && ts.isIdentifier(callee.expression) &&
          TOAST_OBJECTS.has(callee.expression.text) && TOAST_METHODS.has(callee.name.text)) isToast = true
      if (isToast && n.arguments[0]) {
        const e = wrap(n.arguments[0], 'toast')
        if (e) edits.push(e)
      }
    }
    if (ts.isPropertyAssignment(n) && (ts.isIdentifier(n.name) || ts.isStringLiteral(n.name)) && KEYS.has(n.name.text)) {
      if (!isInsideTranslate(n)) {
        const m = messageOf(n.initializer)
        if (usable(m)) {
          const key = n.name.text
          const message = collapse(m.message)
          const [s, e] = at(n)
          const nested = []
          const args = m.args.map((a) => {
            const r = sayNested(a, filename)
            nested.push(...r.messages)
            return r.code
          })
          const call = callKeepingSpaces(m.message, message, args)
          // a getter in a script (read when it is used, not when the list was built); a plain value in a binding
          const text = mode === 'script' ? `get ${key}() { return ${call} }` : `${key}: ${call}`
          const ed = edit(s, e, text, message, `key:${key}`, nested)
          // the other keys of the object: a label with no value, handler or icon beside it may be the action's name
          ed.siblings = ts.isObjectLiteralExpression(n.parent)
            ? n.parent.properties.map((q) => (q.name && q.name.getText ? q.name.getText(sf) : '?'))
            : []
          edits.push(ed)
          return // its parts are inside this edit
        }
      }
    }
    if (mode === 'text' && (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateExpression(n))) {
      if (isDisplayed(n) && !isInsideTranslate(n)) {
        const e = wrap(n, 'literal')
        if (e && !edits.some((x) => x.start <= e.start && e.end <= x.end)) {
          edits.push(e)
          return
        }
      }
    }
    ts.forEachChild(n, visit)
  }
  visit(sf)
  return edits
}

// ------------------------------------------------------------------------------------------------ Vue template

function templateEdits(source, filename, ast) {
  const edits = []
  const left = []

  const handleProps = (el) => {
    for (const p of el.props) {
      if (p.type === 6 /* ATTRIBUTE */ && ATTRS.has(p.name) && p.value) {
        const t = collapse(p.value.content)
        if (isText(t) && !/\{\{|\}\}/.test(t)) {
          edits.push(edit(p.loc.start.offset, p.loc.end.offset,
            `:${p.name}="${htmlAttr(callTranslate(t))}"`, t, `attr:${p.name}`))
        }
      } else if (p.type === 7 /* DIRECTIVE */ && p.exp && p.exp.content) {
        const raw = source.slice(p.exp.loc.start.offset, p.exp.loc.end.offset)
        if (raw !== p.exp.content) continue // entities in the expression: offsets would not match
        const quote = source[p.exp.loc.start.offset - 1]
        if (quote !== '"') continue
        const displayed = p.name === 'bind' && p.arg && p.arg.type === 4 && ATTRS.has(p.arg.content)
        // any other binding, an event handler included: only what an object says and its toast calls
        const mode = displayed ? 'text' : 'binding'
        for (const e of expressionEdits(raw, p.exp.loc.start.offset, mode, filename)) edits.push(e)
      }
    }
  }

  const walk = (children, parent) => {
    // a run of text and interpolations with no element in it is one sentence
    const meaningful = children.filter((c) => c.type !== 3 /* COMMENT */)
    const onlyInline = meaningful.length > 0 && meaningful.every((c) => c.type === 2 || c.type === 5)
    if (onlyInline && meaningful.some((c) => c.type === 2 && WORDS.test(c.content))) {
      const skip = parent && parent.type === 1 && SKIP_TAGS.has(parent.tag)
      if (!skip) {
        let message = ''
        const args = []
        const nestedMessages = []
        let ok = true
        for (const c of meaningful) {
          if (c.type === 2) message += c.content
          else {
            const ex = c.content && c.content.content !== undefined ? c.content.content : ''
            if (!ex || ex.includes('}}')) ok = false
            message += `{${args.length}}`
            const r = sayNested(ex.trim(), filename)
            nestedMessages.push(...r.messages)
            args.push(r.code)
          }
        }
        message = collapse(message)
        if (ok && isText(message) && !/\}\}/.test(message)) {
          const first = meaningful[0]
          const last = meaningful[meaningful.length - 1]
          const start = first.loc.start.offset
          const end = last.loc.end.offset
          const original = source.slice(start, end)
          const lead = original.match(/^\s*/)[0]
          const trail = original.match(/\s*$/)[0]
          edits.push(edit(start, end, `${lead}{{ ${callTranslate(message, args)} }}${trail}`, message, 'text', nestedMessages))
          return
        }
        // not one message: each piece is looked at on its own below
      }
    }
    for (const c of children) {
      if (c.type === 1 /* ELEMENT */) {
        handleProps(c)
        if (!SKIP_TAGS.has(c.tag)) walk(c.children ?? [], c)
      } else if (c.type === 2 /* TEXT */) {
        // a text among elements: a whole sentence only (not the piece of one)
        const t = collapse(c.content)
        if (WORDS.test(t) && !(parent && parent.type === 1 && SKIP_TAGS.has(parent.tag))) {
          const whole = /^[A-ZÀ-Ý0-9]/.test(t) && !/[,(;"']$/.test(t) && !/^[,.;:)\]]/.test(t)
          if (whole && isText(t)) {
            const start = c.loc.start.offset
            const end = c.loc.end.offset
            const original = source.slice(start, end)
            const lead = original.match(/^\s*/)[0]
            const trail = original.match(/\s*$/)[0]
            edits.push(edit(start, end, `${lead}{{ ${callTranslate(t)} }}${trail}`, t, 'text'))
          } else {
            left.push({ line: lineOf(source, c.loc.start.offset), text: t })
          }
        }
      } else if (c.type === 5 /* INTERPOLATION */) {
        const ex = c.content
        const raw = source.slice(ex.loc.start.offset, ex.loc.end.offset)
        if (raw === ex.content) {
          for (const e of expressionEdits(raw, ex.loc.start.offset, 'text', filename)) edits.push(e)
        }
      } else if (c.type === 9 /* IF */ || c.type === 11 /* FOR */) {
        // compiled structural nodes do not occur in an untransformed parse; kept for safety
        if (c.children) walk(c.children, parent)
      } else if (c.children) {
        walk(c.children, parent)
      }
    }
  }
  walk(ast.children ?? [], null)
  return { edits, left }
}

function lineOf(source, offset) {
  let n = 1
  for (let i = 0; i < offset && i < source.length; i++) if (source.charCodeAt(i) === 10) n++
  return n
}

// ------------------------------------------------------------------------------------------------ files

/** Drops an edit that sits inside another, and sorts the rest from the end of the file. */
function settle(edits) {
  const sorted = [...edits].sort((a, b) => a.start - b.start || b.end - a.end)
  const kept = []
  for (const e of sorted) {
    const last = kept[kept.length - 1]
    if (last && e.start < last.end) continue // inside (or overlapping) the one before
    kept.push(e)
  }
  return kept
}

/**
 * Reads one file. Returns { code, messages, left, edits }: `code` is the file with the rewrites applied (the same
 * string when there is none), `messages` the msgids it asks for, `left` the texts it could not take.
 */
export function transformSource(original, filename) {
  let source = original
  const edits = []
  let left = []
  const overridden = []
  for (const o of OVERRIDES) {
    if (!o.file.test(filename)) continue
    if (!source.includes(o.find)) throw new Error(`the text of an override is gone from ${filename}: ${o.find.slice(0, 70)}`)
    source = source.replace(o.find, o.replace)
    overridden.push(...o.messages)
  }
  if (filename.endsWith('.vue')) {
    const { descriptor } = sfc.parse(source, { filename })
    if (descriptor.template && descriptor.template.ast) {
      const t = templateEdits(source, filename, descriptor.template.ast)
      edits.push(...t.edits)
      left = t.left
    }
    for (const block of [descriptor.script, descriptor.scriptSetup]) {
      if (!block) continue
      for (const e of expressionEdits(block.content, block.loc.start.offset, 'script', filename, 0)) edits.push(e)
    }
  } else {
    for (const e of expressionEdits(source, 0, 'script', filename, 0)) edits.push(e)
  }
  const kept = settle(edits.filter((e) => !isKept(filename, e.message)))
  let code = source
  for (const e of [...kept].reverse()) code = code.slice(0, e.start) + e.text + code.slice(e.end)
  // what the overrides ask for is in the code already: it joins the list so the registry has it
  const synthetic = [...overridden, ...kept.flatMap((e) => e.nested ?? [])].map((message) => ({
    start: -1, end: -1, text: '', message, why: 'nested',
  }))
  const all = [...kept, ...synthetic]
  return { code, messages: all.map((e) => e.message), left, edits: all, changed: kept.length > 0 || overridden.length > 0 }
}

/** Every file of the scoped apps under `frontendDir`. */
export function* scopedFiles(frontendDir) {
  const walk = function* (dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) yield* walk(full)
      else if (isInScope(full)) yield full
    }
  }
  yield* walk(path.join(frontendDir, 'src', 'apps'))
}

/** The sorted msgids of the scoped apps, with where each is asked for. */
export function collectMessages(frontendDir) {
  const where = new Map()
  const left = []
  for (const file of scopedFiles(frontendDir)) {
    const rel = path.relative(frontendDir, file).split(path.sep).join('/')
    const { messages, left: l, edits } = transformSource(fs.readFileSync(file, 'utf8'), file)
    edits.forEach((e) => {
      if (!where.has(e.message)) where.set(e.message, [])
      where.get(e.message).push(rel)
    })
    for (const x of l) left.push({ file: rel, ...x })
  }
  return { messages: [...where.keys()].sort((a, b) => a.localeCompare(b, 'en')), where, left }
}

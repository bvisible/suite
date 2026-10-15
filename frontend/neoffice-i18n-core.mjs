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
// ////
// //// frappe-ui's editor (the toolbar, the slash menu, the table, link and media tools and the dialogs of Writer's page,
// //// which Mail's composer shows too) is English only upstream as well: its files are read the same way, one by one
// //// (FRAPPE_UI_EDITOR_FILES), and the few texts that are passed as arguments are said by OVERRIDES. The rest of
// //// frappe-ui (its components: pickers, dialogs, lists) is not read here: that is a decision of its own.
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const sfc = require('@vue/compiler-sfc')
const ts = require('typescript')

/**
 * What this module reads of the suite's own frontend: the apps upstream wrote without __() (Sheets, Slides, Writer, most
 * of the Drive) and the parts the others left English (Mail's settings, Meet, Calendar's filters, the shell, the shared
 * components). A text already said through __() is never touched, so a file that is entirely wrapped is a no-op.
 * Never read: our own modules (src/neoffice), the translation boot, the tests, and what runs in a worker (no __ there).
 */
export const SCOPE =
  /[\\/]frontend[\\/]src[\\/](?:apps[\\/](?:sheets|slides|writer|drive|mail|calendar|meet)[\\/]|apps[\\/]registry\.ts$|shell[\\/]|components[\\/]|composables[\\/]|utils[\\/]|router[\\/])/
const NEVER = /[\\/]src[\\/]apps[\\/]mail[\\/]sw\.ts$|[\\/]service-worker\.js$|[Ww]orker\.ts$/
/** The folders of src/ the registry generator walks (isInScope keeps what is read). */
const SRC_DIRS = ['apps', 'shell', 'components', 'composables', 'utils', 'router']

/**
 * The files of frappe-ui's editor that are read (path under frappe-ui/src/molecules/editor/). Listed one by one, not by
 * folder: each was looked at, and a new file of a later release is not said until somebody has looked at it too.
 * Left out on purpose: extensions/toc-node/toc-node-extension.ts (its 'Table of Contents' is the title stored in the
 * document), extensions/iframe/iframe-embed-utils.ts (the names of the platforms are brands).
 */
const FRAPPE_UI_EDITOR_FILES = new Set([
  'commands.ts',
  'menu.ts',
  'components/AttachmentNodeView.vue',
  'components/EditorDropZone.vue',
  'components/ImageViewerModal.vue',
  'components/MediaNodeView.vue',
  'components/MediaResizeHandle.vue',
  'components/MediaToolbar.vue',
  'components/UploadProgressIndicator.vue',
  'components/VideoControls.vue',
  'components/font-color/fontColorController.ts',
  'components/font-color/swatches.ts',
  'components/image-viewer/ImageViewerControlsBar.vue',
  'components/table-color/tableCellColorController.ts',
  'components/table-size-picker/TableSizePicker.vue',
  'composables/useFloatingPopup.ts',
  'extensions/code-block/CodeBlockComponent.vue',
  'extensions/iframe/IframeInsertDialog.vue',
  'extensions/iframe/IframeNodeView.vue',
  'extensions/iframe/iframeInsertDialogController.ts',
  'extensions/iframe/useIframeDialog.ts',
  'extensions/image-group/ImageGroupGridCell.vue',
  'extensions/image-group/ImageGroupNodeView.vue',
  'extensions/image-group/ImageGroupUploadDialog.vue',
  'extensions/image-group/image-group-utils.ts',
  'extensions/image-group/imageGroupDialogController.ts',
  'extensions/image-group/useImageGroupDialog.ts',
  'extensions/image-viewer/imageViewerController.ts',
  'extensions/link/LinkEditorPopup.vue',
  'extensions/slash-commands/slash-commands-extension.ts',
  'extensions/suggestion/SuggestionList.vue',
  'extensions/toc-node/TocNodeView.vue',
])
/**
 * The shared components and the experimental editor of frappe-ui that the suite uses, read file by file (path under
 * the package) like the editor above: each was looked at, the pop-ups they mount on their own are given the page's __
 * (OVERRIDES), and a file of a later release is not said before somebody has looked at it.
 * Left out: experimental/Calendar (neoffice-calendar-i18n.ts says it), Charts and FloatingWindow (not used here),
 * TextEditor/extensions/toc-node/toc-node-extension.ts (its title is stored in the document).
 */
const FRAPPE_UI_COMPONENT_FILES = [
  'Alert/Alert.vue', 'BottomSheet/BottomSheet.vue', 'Combobox/Combobox.vue', 'Combobox/ComboboxResults.vue',
  'DatePicker/CalendarPanel.vue', 'DatePicker/DatePicker.vue', 'DatePicker/DateRangePicker.vue',
  'DatePicker/DateTimePicker.vue', 'Dialog/Dialog.vue', 'Dropdown/Dropdown.vue', 'FileUploader/FileUploader.vue',
  'KeyboardShortcutsDialog/KeyboardShortcutsDialog.vue', 'LoadingText/LoadingText.vue', 'Menu/Menu.vue',
  'MultiSelect/MultiSelect.vue', 'MultiSelect/MultiSelectResults.vue', 'PageHeader/PageHeaderBackButton.vue',
  'Password/Password.vue', 'Rating/Rating.vue', 'Select/Select.vue', 'SettingsDialog/SettingsDialog.vue',
  'Sidebar/SidebarCard.vue', 'Sidebar/SidebarCollapseToggle.vue', 'Sidebar/SidebarHeader.vue', 'Spinner/Spinner.vue',
  'TimePicker/TimePicker.vue', 'Tree/TreeItem.vue',
]
const FRAPPE_UI_EXPERIMENTAL_FILES = [
  'ListView/ListFooter.vue', 'ListView/ListSelectBanner.vue', 'ListView/ListView.vue',
  'CommandPalette/CommandPalette.vue', 'CommandPalette/CommandPaletteInput.vue', 'SpriteIcons/IconPicker.vue',
  'TextEditor/commands.js', 'TextEditor/components/FontColor.vue', 'TextEditor/components/ImageViewerModal.vue',
  'TextEditor/components/LinkPopup.vue', 'TextEditor/components/MediaNodeView.vue',
  'TextEditor/extensions/iframe/IframeNodeView.vue', 'TextEditor/extensions/iframe/InsertIframe.vue',
  'TextEditor/extensions/image-group/ImageGroupNodeView.vue',
  'TextEditor/extensions/image-group/ImageGroupUploadDialog.vue',
  'TextEditor/extensions/image-viewer-extension.ts', 'TextEditor/extensions/link/link-extension.ts',
  'TextEditor/extensions/slash-commands/slash-commands-extension.ts',
  'TextEditor/extensions/suggestion/SuggestionList.vue', 'TextEditor/extensions/toc-node/TocNodeView.vue',
]
/** Every file of the library that is read, path under the package. */
const FRAPPE_UI_FILES = new Set([
  ...[...FRAPPE_UI_EDITOR_FILES].map((f) => `src/molecules/editor/${f}`),
  'src/utils/dialog.ts',
  'src/molecules/list/ListHeader.vue',
  ...FRAPPE_UI_COMPONENT_FILES.map((f) => `src/components/${f}`),
  ...FRAPPE_UI_EXPERIMENTAL_FILES.map((f) => `experimental/${f}`),
])
const FRAPPE_UI = /[\\/]frappe-ui[\\/]((?:src|experimental)[\\/].+)$/
/** Where those files sit under the frontend folder (the registry generator reads them from there). */
export const FRAPPE_UI_PATHS = [...FRAPPE_UI_FILES].map((rel) => ['node_modules', 'frappe-ui', ...rel.split('/')])
const isFrappeUiFile = (file) => {
  const m = FRAPPE_UI.exec(file)
  return Boolean(m) && FRAPPE_UI_FILES.has(m[1].split('\\').join('/'))
}
// A library has a src/components and a src/utils too (frappe-ui sits under node_modules, or as the repository's
// submodule next to frontend/): SCOPE names OUR frontend/src, and a library is read only through the list above.
export const isInScope = (file) =>
  ((SCOPE.test(file) && !/[\\/]node_modules[\\/]/.test(file)) || isFrappeUiFile(file)) &&
  !NEVER.test(file) &&
  /\.(vue|js|ts)$/.test(file) &&
  !/\.(test|spec)\.|\.d\.ts$/.test(file)

/** Attributes of a template whose value a person reads. */
const ATTRS = new Set([
  'label', 'title', 'placeholder', 'description', 'aria-label', 'alt', 'tooltip', 'text', 'message', 'subtitle',
  'confirm-label', 'cancel-label', 'header', 'hint', 'empty-text', 'no-results-text', 'helper-text', 'dialog-label',
])
/** Keys of an object whose string value a person reads. */
const KEYS = new Set([
  'title', 'label', 'message', 'description', 'placeholder', 'text', 'tooltip', 'subtitle', 'hint', 'header',
  'emptyText', 'confirmLabel', 'cancelLabel', 'successMessage', 'errorMessage', 'loadingMessage', 'toastMessage',
  'group', 'defaultLabel',
])
/**
 * Functions whose returned literals are only ever shown (checked one by one: a function that returns a name the code
 * looks up again — recencyBucket in Sheets — must not be here), and the keys of an object whose value is such a function.
 */
const DISPLAY_FUNCTIONS = new Set([
  'formatDate', 'commentTime', '_fillSummary', 'cfRuleLabel', 'dayLabel', 'entityLabel', 'itemString',
  '_validateName', '_validateRange',
])
const RETURNING_KEYS = new Set(['validate', 'success', 'error', 'loading', 'getLabel'])
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
    // the styling of the Present button asks for the action by its English label: ask by its icon, so the label can be said
    file: /slides[\\/]components[\\/]PresentationPreview\.vue$/,
    find: '<div :class="getActionButtonClasses(action.label)" @click="action.onClick">',
    replace: '<div :class="getActionButtonClasses(action.icon === Presentation ? \'Present\' : \'\')" @click="action.onClick">',
    messages: [],
  },
  {
    file: /slides[\\/]components[\\/]PresentationPreview\.vue$/,
    find: ':class="getActionIconClasses(action.label)"',
    replace: ':class="getActionIconClasses(action.icon === Presentation ? \'Present\' : \'\')"',
    messages: [],
  },
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

// What the plugin cannot see by itself, said from the exact upstream text (maintenance#1592): a text that is the argument
// of a function, a count built by concatenation, a title that is data shown as text, a layout the French text overflows.
// `all: true` says every occurrence of the text; a message with a context is written 'msgid\u0004context'.
const FRAPPE_UI_TABLE_LABELS = [
  'Insert column left', 'Insert column right', 'Delete column', 'Insert row above', 'Insert row below', 'Delete row',
  'Toggle header row', 'Merge or split cells', 'Delete table',
]
OVERRIDES.push(
  // ---- Slides
  {
    file: /slides[\\/]components[\\/]ThemeDialog\.vue$/,
    find: "(props.update ? 'Set theme' : 'Select theme')",
    replace: "(props.update ? __('Set theme') : __('Select theme'))",
    messages: ['Set theme', 'Select theme'],
  },
  {
    file: /slides[\\/]components[\\/]ThemeDialog\.vue$/,
    find: "\t\t? 'Update the theme for this presentation. All newly added slides will use this theme.'\n" +
      "\t\t: 'Select a theme for your new presentation. You can change this theme later.',",
    replace: "\t\t? __('Update the theme for this presentation. All newly added slides will use this theme.')\n" +
      "\t\t: __('Select a theme for your new presentation. You can change this theme later.'),",
    messages: [
      'Update the theme for this presentation. All newly added slides will use this theme.',
      'Select a theme for your new presentation. You can change this theme later.',
    ],
  },
  {
    // the title of a theme is data (the code tells Light and Dark apart by it): what is shown is said
    file: /slides[\\/]components[\\/]ThemeDialog\.vue$/,
    find: '{{ theme.title }}',
    replace: '{{ __(theme.title) }}',
    messages: ['Light', 'Dark'],
  },
  {
    // the header of the properties panel names the kind of element, built from its type
    file: /slides[\\/]components[\\/]PropertiesPanel\.vue$/,
    find: "\tif (count > 1) return `${count} elements`\n" +
      "\tconst type = activeElement.value?.type\n" +
      "\treturn type ? type[0].toUpperCase() + type.slice(1) : ''",
    replace: "\tif (count > 1) return __('{0} elements', [count])\n" +
      "\tconst type = activeElement.value?.type\n" +
      "\treturn type ? __(type[0].toUpperCase() + type.slice(1)) : ''",
    messages: ['{0} elements', 'Text', 'Shape', 'Image', 'Video', 'Table'],
  },
  // ---- Sheets
  {
    // the owner column of the list of sheets says « me » for the person's own sheets
    file: /sheets[\\/]pages[\\/]Home\.vue$/,
    find: "if (sheet.is_owner) return 'me'",
    replace: "if (sheet.is_owner) return __('me', null, 'owner of a sheet')",
    messages: ['me\u0004owner of a sheet'],
  },
  {
    // « Restaurer » and « Supprimer définitivement » do not fit the 220px that « Restore » and « Delete forever » did
    file: /sheets[\\/]pages[\\/]Trash\.vue$/,
    find: "{ label: '', key: '_actions', width: '220px', align: 'right' }",
    replace: "{ label: '', key: '_actions', width: '320px', align: 'right' }",
    messages: [],
  },
  {
    // what the version list says about a snapshot (op_labels[0]); the kind itself stays what the code reads
    file: /sheets[\\/]services[\\/]versions\.js$/,
    find: "\tif (item.kind === 'milestone') return ['Milestone']\n" +
      "\tif (item.kind === 'named')     return ['Named version']\n" +
      "\tif (item.op_count > 0)         return [`${item.op_count} edit${item.op_count === 1 ? '' : 's'}`]",
    replace: "\tif (item.kind === 'milestone') return [__('Milestone')]\n" +
      "\tif (item.kind === 'named')     return [__('Named version')]\n" +
      "\tif (item.op_count > 0)         return [item.op_count === 1 ? __('1 edit') : __('{0} edits', [item.op_count])]",
    messages: ['Milestone', 'Named version', '1 edit', '{0} edits'],
  },
  // ---- Drive
  {
    // the size column: a count of items / slides built by concatenation (« 3 items »)
    file: /drive[\\/]components[\\/]DriveListRow\.vue$/,
    find: "      ? row.child_count + ' item' + (row.child_count === 1 ? '' : 's')\n" +
      "      : 'empty'\n" +
      "  if (row.slide_count != null)\n" +
      "    return row.slide_count\n" +
      "      ? row.slide_count + ' slide' + (row.slide_count === 1 ? '' : 's')\n" +
      "      : 'empty'",
    replace: "      ? (row.child_count === 1 ? __('1 item') : __('{0} items', [row.child_count]))\n" +
      "      : __('empty')\n" +
      "  if (row.slide_count != null)\n" +
      "    return row.slide_count\n" +
      "      ? (row.slide_count === 1 ? __('1 slide') : __('{0} slides', [row.slide_count]))\n" +
      "      : __('empty')",
    messages: ['1 item', '{0} items', 'empty', '1 slide', '{0} slides'],
  },
  {
    // « Responsable », « Dernière modification », « 1 diapositive » and « 3 éléments » do not fit the 10%, 15% and 8%
    // that « Owner », « Last Modified », « 1 slide » and « 3 items » did
    file: /drive[\\/]data[\\/]listColumns\.ts$/,
    find: "          '10%',\n          '15%',\n          route.name === 'drive-Attachments' ? '25%' : '8%',",
    replace: "          '12%',\n          '18%',\n          route.name === 'drive-Attachments' ? '25%' : '11%',",
    messages: [],
  },
  {
    file: /drive[\\/]components[\\/]GridItem\.vue$/,
    find: "  if (!props.file.child_count) return 'empty'\n" +
      "  return props.file.child_count + ' item' + (props.file.child_count === 1 ? '' : 's')",
    replace: "  if (!props.file.child_count) return __('empty')\n" +
      "  return props.file.child_count === 1 ? __('1 item') : __('{0} items', [props.file.child_count])",
    messages: ['empty', '1 item', '{0} items'],
  },
  {
    // the root of the folder tree is called « Home » in the breadcrumb: say it like the tab above it
    file: /drive[\\/]ui[\\/]drive[\\/]components[\\/]MoveDialog\.vue$/,
    find: "file_name: 'Home'",
    replace: "get file_name() { return __('Home') }",
    all: true,
    messages: ['Home'],
  },
  {
    file: /drive[\\/]ui[\\/]drive[\\/]components[\\/]MoveDialog\.vue$/,
    find: "file_name: 'Site'",
    replace: "get file_name() { return __('Site') }",
    all: true,
    messages: ['Site'],
  },
  {
    file: /drive[\\/]ui[\\/]drive[\\/]components[\\/]MoveDialog\.vue$/,
    find: "? 'Home' : k.file_name,",
    replace: "? __('Home') : k.file_name,",
    messages: ['Home'],
  },
  {
    // emptying the trash is an action; the bare « Empty » is the state of a list (« Vide »)
    file: /drive[\\/]components[\\/]Navbar\.vue$/,
    find: "label: __('Empty'),",
    replace: "label: __('Empty', null, 'Trash'),",
    messages: ['Empty\u0004Trash'],
  },
  // ---- the shell
  {
    // « Click to invert / edit »: the verb is chosen by the code and spliced into the sentence: two whole sentences
    file: /shell[\\/]SuiteCommandPalette\.vue$/,
    find: ":text=\"`Click to ${mailFilterVerb(filter.key).toLowerCase()}`\"",
    replace: ":text=\"canInvertMailFilter(filter.key) ? __('Click to invert') : __('Click to edit')\"",
    messages: ['Click to invert', 'Click to edit'],
  },
  {
    file: /shell[\\/]SuiteCommandPalette\.vue$/,
    find: ":aria-label=\"`${mailFilterVerb(filter.key)} ${getMailFilterLabel(filter)}`\"",
    replace: ":aria-label=\"canInvertMailFilter(filter.key) ? __('Invert {0}', [getMailFilterLabel(filter)]) : __('Edit {0}', [getMailFilterLabel(filter)])\"",
    messages: ['Invert {0}', 'Edit {0}'],
  },
  // ---- Meet
  {
    // the verb of the sentence is chosen by the code: two sentences, so each is a whole message
    file: /apps[\\/]meet[\\/]composables[\\/]useCaptions\.ts$/,
    find: '`Failed to ${requestedEnabled ? "enable" : "disable"} captions`',
    replace: "requestedEnabled ? __('Failed to enable captions') : __('Failed to disable captions')",
    messages: ['Failed to enable captions', 'Failed to disable captions'],
  },
  // ---- frappe-ui's experimental editor (Mail's composer)
  {
    // the pagination of a list: « of » is a word between two numbers (a context: the bare word is « de » elsewhere)
    file: /frappe-ui[\\/]experimental[\\/]ListView[\\/]ListFooter\.vue$/,
    find: '<div>of</div>',
    replace: "<div>{{ __('of', null, 'pagination') }}</div>",
    messages: ['of\u0004pagination'],
  },
  {
    // « Uploading video... / image... »: the noun is chosen by the code, so each sentence is whole
    file: /frappe-ui[\\/]experimental[\\/]TextEditor[\\/]components[\\/]MediaNodeView\.vue$/,
    find: "Uploading {{ isVideo ? 'video' : 'image' }}...",
    replace: "{{ isVideo ? __('Uploading video...') : __('Uploading image...') }}",
    messages: ['Uploading video...', 'Uploading image...'],
  },
  {
    file: /frappe-ui[\\/]experimental[\\/]TextEditor[\\/]components[\\/]MediaNodeView\.vue$/,
    find: "This {{ isVideo ? 'video' : 'image' }} hasn't yet been uploaded.",
    replace: "{{ isVideo ? __('This video hasn\\'t yet been uploaded.') : __('This image hasn\\'t yet been uploaded.') }}",
    messages: ["This video hasn't yet been uploaded.", "This image hasn't yet been uploaded."],
  },
  {
    // the image viewer and the link pop-up are apps of their own (createApp): they are given the page's __
    file: /frappe-ui[\\/]experimental[\\/]TextEditor[\\/]extensions[\\/]image-viewer-extension\.ts$/,
    find: '  app.mount(container)\n',
    replace: "  app.config.globalProperties.__ = (...args: unknown[]) => (window as any).__(...args)\n  app.mount(container)\n",
    messages: [],
  },
  {
    file: /frappe-ui[\\/]experimental[\\/]TextEditor[\\/]extensions[\\/]link[\\/]link-extension\.ts$/,
    find: '    app.mount(container)\n',
    replace: "    app.config.globalProperties.__ = (...args: unknown[]) => (window as any).__(...args)\n    app.mount(container)\n",
    messages: [],
  },
  // ---- frappe-ui's confirmation dialogs (every confirm of the Drive and of Writer)
  {
    file: /frappe-ui[\\/]src[\\/]utils[\\/]dialog\.ts$/,
    find: "args.confirmLabel || 'Confirm'",
    replace: "args.confirmLabel || __('Confirm')",
    messages: ['Confirm'],
  },
  {
    file: /frappe-ui[\\/]src[\\/]utils[\\/]dialog\.ts$/,
    find: "args.cancelLabel || 'Cancel'",
    replace: "args.cancelLabel || __('Cancel')",
    all: true,
    messages: ['Cancel'],
  },
  {
    file: /frappe-ui[\\/]src[\\/]utils[\\/]dialog\.ts$/,
    find: "args.confirmLabel || 'Submit'",
    replace: "args.confirmLabel || __('Submit')",
    messages: ['Submit'],
  },
  {
    file: /frappe-ui[\\/]src[\\/]utils[\\/]dialog\.ts$/,
    find: "args.confirmLabel ?? 'Delete'",
    replace: "args.confirmLabel ?? __('Delete')",
    messages: ['Delete'],
  },
  // ---- frappe-ui's editor (Writer's page, Mail's composer)
  {
    // The pop-ups and dialogs of the editor are apps of their own (createApp), not children of the page's: __ in a
    // template is a property of the app, and they do not have it (« e.__ is not a function » at render).
    file: /molecules[\\/]editor[\\/]composables[\\/]useFloatingPopup\.ts$/,
    find: '  app.mount(floating)\n',
    replace: "  app.config.globalProperties.__ = (...args: unknown[]) => (window as any).__(...args)\n  app.mount(floating)\n",
    messages: [],
  },
  {
    file: /molecules[\\/]editor[\\/]extensions[\\/]image-group[\\/]imageGroupDialogController\.ts$/,
    find: '  app.mount(container)\n',
    replace: "  app.config.globalProperties.__ = (...args: unknown[]) => (window as any).__(...args)\n  app.mount(container)\n",
    messages: [],
  },
  {
    file: /molecules[\\/]editor[\\/]extensions[\\/]iframe[\\/]iframeInsertDialogController\.ts$/,
    find: '  app.mount(container)\n',
    replace: "  app.config.globalProperties.__ = (...args: unknown[]) => (window as any).__(...args)\n  app.mount(container)\n",
    messages: [],
  },
  {
    file: /molecules[\\/]editor[\\/]extensions[\\/]image-viewer[\\/]imageViewerController\.ts$/,
    find: '  app.mount(container)\n',
    replace: "  app.config.globalProperties.__ = (...args: unknown[]) => (window as any).__(...args)\n  app.mount(container)\n",
    messages: [],
  },
  {
    // the commands are built when the module loads, before the translations: the label is read when it is shown
    file: /molecules[\\/]editor[\\/]menu\.ts$/,
    find: '    label: meta.label,\n    icon: meta.icon,',
    replace: '    get label() { return meta.label },\n    icon: meta.icon,',
    messages: [],
  },
  {
    // the table commands take their label as an argument; TableMergeOrSplit spreads one of them when the module loads,
    // before __ is installed, hence the typeof (its getLabel is what is shown)
    file: /molecules[\\/]editor[\\/]menu\.ts$/,
    find: '  return {\n    label,\n    icon,\n    action,\n    isActive,',
    replace: "  return {\n    get label() { return typeof __ === 'function' ? __(label) : label },\n    icon,\n    action,\n    isActive,",
    messages: FRAPPE_UI_TABLE_LABELS,
  },
  {
    // the headings of the groups of the slash menu
    file: /molecules[\\/]editor[\\/]extensions[\\/]slash-commands[\\/]slash-commands-extension\.ts$/,
    find: '  return items.map((item) => ({ ...item, group }))',
    replace: '  return items.map((item) => ({ ...item, group: __(group) }))',
    messages: ['Text', 'Lists', 'Media', 'Embeds', 'Insert'],
  },
  {
    // the names of the colours of the palette (the value stored on the mark stays the lowercase name)
    file: /molecules[\\/]editor[\\/]components[\\/]font-color[\\/]swatches\.ts$/,
    find: '    label: capitalize(color.name),\n',
    replace: '    get label() { return __(capitalize(color.name)) },\n',
    messages: ['Red', 'Orange', 'Yellow', 'Green', 'Teal', 'Cyan', 'Blue', 'Indigo', 'Purple', 'Pink', 'Gray'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]font-color[\\/]fontColorController\.ts$/,
    find: "dialogLabel: 'Text and background color',",
    replace: "dialogLabel: __('Text and background color'),",
    messages: ['Text and background color'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]font-color[\\/]fontColorController\.ts$/,
    find: "h('div', { class: 'text-sm text-ink-gray-7' }, 'Text Color'),",
    replace: "h('div', { class: 'text-sm text-ink-gray-7' }, __('Text Color')),",
    messages: ['Text Color'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]font-color[\\/]fontColorController\.ts$/,
    find: "                'Background Color',\n",
    replace: "                __('Background Color'),\n",
    messages: ['Background Color'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]table-color[\\/]tableCellColorController\.ts$/,
    find: "{ dialogLabel: 'Cell color', contentClass: 'rounded-5 p-2.5' }",
    replace: "{ dialogLabel: __('Cell color'), contentClass: 'rounded-5 p-2.5' }",
    messages: ['Cell color'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]table-color[\\/]tableCellColorController\.ts$/,
    find: "h('div', { class: 'text-sm text-ink-gray-7' }, 'Cell color'),",
    replace: "h('div', { class: 'text-sm text-ink-gray-7' }, __('Cell color')),",
    messages: ['Cell color'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]table-color[\\/]tableCellColorController\.ts$/,
    find: "h('div', { class: 'mt-4 text-sm text-ink-gray-7' }, 'Text color'),",
    replace: "h('div', { class: 'mt-4 text-sm text-ink-gray-7' }, __('Text color')),",
    messages: ['Text color'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]MediaToolbar\.vue$/,
    find: "      image: 'Replace image',\n      video: 'Replace video',\n      embed: 'Change link',",
    replace: "      image: __('Replace image'),\n      video: __('Replace video'),\n      embed: __('Change link'),",
    messages: ['Replace image', 'Replace video', 'Change link'],
  },
  {
    file: /molecules[\\/]editor[\\/]components[\\/]EditorDropZone\.vue$/,
    find: "    return videoCount === 1 ? 'Drop video to upload' : 'Drop videos to upload'\n" +
      "  if (imageCount > 1) return 'Drop images to create gallery'\n" +
      "  if (imageCount === 1) return 'Drop image to upload'",
    replace: "    return videoCount === 1 ? __('Drop video to upload') : __('Drop videos to upload')\n" +
      "  if (imageCount > 1) return __('Drop images to create gallery')\n" +
      "  if (imageCount === 1) return __('Drop image to upload')",
    messages: ['Drop video to upload', 'Drop videos to upload', 'Drop images to create gallery', 'Drop image to upload'],
  },
  {
    // the noun inside the sentence is « video » or « image »: two sentences, so each can agree in gender
    file: /molecules[\\/]editor[\\/]components[\\/]MediaNodeView\.vue$/,
    find: "          This {{ isVideo ? 'video' : 'image' }} hasn't yet been uploaded.\n",
    replace: "          {{ isVideo ? __('This video hasn\\'t yet been uploaded.') : __('This image hasn\\'t yet been uploaded.') }}\n",
    messages: ["This video hasn't yet been uploaded.", "This image hasn't yet been uploaded."],
  },
  {
    // the name a file has when it has none
    file: /molecules[\\/]editor[\\/]components[\\/]AttachmentNodeView\.vue$/,
    find: "props.node.attrs.fileName || 'Attachment')",
    replace: "props.node.attrs.fileName || __('Attachment'))",
    messages: ['Attachment'],
  },
  {
    // the title of the embed dialog is the result of a function: a verb for the editing, a name for a platform
    file: /molecules[\\/]editor[\\/]extensions[\\/]iframe[\\/]IframeInsertDialog\.vue$/,
    find: "  if (isEditing.value) return 'Edit Embed'\n" +
      "  return platformConfig.value\n" +
      "    ? `Embed ${platformConfig.value.name}`\n" +
      "    : 'Insert Embed'",
    replace: "  if (isEditing.value) return __('Edit Embed')\n" +
      "  return platformConfig.value\n" +
      "    ? __('Embed {0}', [platformConfig.value.name])\n" +
      "    : __('Insert Embed')",
    messages: ['Edit Embed', 'Embed {0}', 'Insert Embed'],
  },
  {
    // « Valid Generic URL »: the name of the platform when the address is none in particular
    file: /molecules[\\/]editor[\\/]extensions[\\/]iframe[\\/]useIframeDialog\.ts$/,
    find: "    if (!isValidUrl.value) return 'Generic'\n" +
      "    return detectPlatform(processedUrl.value)?.name ?? 'Generic'",
    replace: "    if (!isValidUrl.value) return __('Generic')\n" +
      "    return detectPlatform(processedUrl.value)?.name ?? __('Generic')",
    messages: ['Generic'],
  },
  {
    file: /molecules[\\/]editor[\\/]extensions[\\/]iframe[\\/]useIframeDialog\.ts$/,
    find: "        'Failed to insert embed. Please check the URL and try again.'\n",
    replace: "        __('Failed to insert embed. Please check the URL and try again.')\n",
    messages: ['Failed to insert embed. Please check the URL and try again.'],
  },
  {
    // the text the « / » menu puts in the document before the link pop-up opens: a word of the reader's language, and
    // the selection that the pop-up reads is as long as that word
    file: /molecules[\\/]editor[\\/]extensions[\\/]slash-commands[\\/]slash-commands-extension\.ts$/,
    find: "        .insertContent('Link')\n        .setTextSelection({ from, to: from + 4 })",
    replace: "        .insertContent(__('Link'))\n        .setTextSelection({ from, to: from + __('Link').length })",
    messages: ['Link'],
  },
  {
    file: /molecules[\\/]editor[\\/]extensions[\\/]image-group[\\/]useImageGroupDialog\.ts$/,
    find: "        ? 'Upload cancelled'\n        : (error as Error)?.message || 'Upload failed'",
    replace: "        ? __('Upload cancelled')\n        : (error as Error)?.message || __('Upload failed')",
    messages: ['Upload cancelled', 'Upload failed'],
  },
  {
    file: /molecules[\\/]editor[\\/]extensions[\\/]iframe[\\/]useIframeDialog\.ts$/,
    find: "        ? 'Please enter a supported URL or iframe embed code'\n",
    replace: "        ? __('Please enter a supported URL or iframe embed code')\n",
    messages: ['Please enter a supported URL or iframe embed code'],
  },
  {
    file: /molecules[\\/]editor[\\/]extensions[\\/]image-group[\\/]ImageGroupUploadDialog\.vue$/,
    find: "  if (count > 1) return `Insert ${count} images`\n  return 'Insert image'",
    replace: "  if (count > 1) return __('Insert {0} images', [count])\n  return __('Insert image')",
    messages: ['Insert {0} images', 'Insert image'],
  },

  // the pagination of the list of sheets (« 1 of 1 »): « of » is a word on its own between two values, with a context
  // because the bare word is « de » elsewhere
  {
    file: /sheets[\\/]pages[\\/]Home\.vue$/,
    find: '<span>of</span>',
    replace: "<span>{{ __('of', null, 'pagination') }}</span>",
    messages: ['of\u0004pagination'],
  },
  {
    // the banner of a version preview: a number then the noun, built with a plural
    file: /sheets[\\/]components[\\/]SheetEditor[\\/]VersionPreviewBanner\.vue$/,
    find: "<b>{{ diff.total_changed_cells }}</b> edit{{ diff.total_changed_cells === 1 ? '' : 's' }}",
    replace: "<b>{{ diff.total_changed_cells }}</b> {{ diff.total_changed_cells === 1 ? __('edit') : __('edits') }}",
    messages: ['edit', 'edits'],
  },
  {
    file: /sheets[\\/]components[\\/]SheetEditor[\\/]VersionPreviewBanner\.vue$/,
    find: "({{ diff.total_changed_rows }} row{{ diff.total_changed_rows === 1 ? '' : 's' }} changed)",
    replace: "({{ diff.total_changed_rows }} {{ diff.total_changed_rows === 1 ? __('row changed') : __('rows changed') }})",
    messages: ['row changed', 'rows changed'],
  },
  // ---- Writer
  {
    file: /writer[\\/]components[\\/]SearchDialog\.vue$/,
    find: '><KeyboardShortcut combo="Enter" /> to search</span',
    replace: "><KeyboardShortcut combo=\"Enter\" /> {{ __('to search') }}</span",
    messages: ['to search'],
  },
  {
    file: /writer[\\/]components[\\/]SearchDialog\.vue$/,
    find: 'Showing results for "<span class="font-medium">{{ query }}</span',
    replace: '{{ __(\'Showing results for\') }} "<span class="font-medium">{{ query }}</span',
    messages: ['Showing results for'],
  },
  // ---- Drive
  {
    // the marker of the folder the item is in, in the tree of the Move dialog
    file: /drive[\\/]ui[\\/]drive[\\/]components[\\/]MoveDialog\.vue$/,
    find: '(current)</span></span>',
    replace: "{{ __('(current)') }}</span></span>",
    messages: ['(current)'],
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
          // a getter in a script (read when it is used, not when the list was built); a plain value in a binding.
          // A getter can be read before the translations are loaded (vue-router copies a route's `meta` when it is
          // installed, 15.10: « __ is not defined », the whole Suite blank): `__` is the global that boot/translation.ts sets
          // once the catalogue is there, so until then the getter gives the text as the source wrote it.
          const original = srcOf(n.initializer)
          const text =
            mode === 'script'
              ? `get ${key}() { return typeof __ === 'function' ? ${call} : ${original} }`
              : `${key}: ${call}`
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
    // `all`: every occurrence (the same text said in several places); a function so that `$&` in a text stays a text
    source = o.all ? source.split(o.find).join(o.replace) : source.replace(o.find, () => o.replace)
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
  // an override that says no message (a line added around a mount) is a change too: compare the text
  return { code, messages: all.map((e) => e.message), left, edits: all, changed: code !== original }
}

/** Every file of the suite's frontend that is read under `frontendDir`, and the files of frappe-ui that are read. */
export function* scopedFiles(frontendDir) {
  const walk = function* (dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) yield* walk(full)
      else if (isInScope(full)) yield full
    }
  }
  for (const dir of SRC_DIRS) {
    const root = path.join(frontendDir, 'src', dir)
    if (fs.existsSync(root)) yield* walk(root)
  }
  for (const parts of FRAPPE_UI_PATHS) {
    const file = path.join(frontendDir, ...parts)
    if (fs.existsSync(file) && isInScope(file)) yield file
  }
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

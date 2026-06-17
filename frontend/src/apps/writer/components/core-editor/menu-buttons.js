import { h, defineAsyncComponent } from 'vue'

import ManageFont from '@/apps/writer/components/ManageFont.vue'

import LucidePaintRoller from '~icons/lucide/paint-roller'
import LucideBrushCleaning from '~icons/lucide/brush-cleaning'
import LucideSettings from '~icons/lucide/settings'
import LucideForm from '~icons/lucide/sticky-note'
import LucideAlignVerticalSpacingAround from '~icons/lucide/align-vertical-space-around'

const EXTRA_BUTTON_PREDICATES = [
  (e) => e.can().sinkListItem('listItem'),
  (e) => e.can().liftListItem('listItem'),
]

const TABLE_BUTTONS = [
  'InsertTable',
  'AddColumnBefore',
  'AddColumnAfter',
  'DeleteColumn',
  'AddRowBefore',
  'AddRowAfter',
  'DeleteRow',
  'MergeCells',
  'SplitCell',
  'ToggleHeaderColumn',
  'ToggleHeaderRow',
  'ToggleHeaderCell',
  'DeleteTable',
]

export function buildMenuButtons({ editor, settings, isPainting, openSettings }) {
  return [
    ['Paragraph', 'Heading 1', 'Heading 2', 'Heading 3', 'Heading 4'],
    'Bold',
    'Italic',
    'Underline',
    'Strikethrough',
    'Link',
    'FontColor',
    ['Align Left', 'Align Center', 'Align Right'],
    {
      label: 'Paint Styles',
      icon: LucidePaintRoller,
      isActive: () => isPainting.value,
      action: (e) => {
        e.commands.focus()
        e.commands.storeStyles()
      },
    },
    {
      label: 'Clear formatting',
      icon: LucideBrushCleaning,
      isActive: () => false,
      action: (e) => {
        e.commands.focus()
        e.commands.clearStyles()
        e.commands.cleanStyles()
      },
    },
    'Separator',
    {
      label: 'FontOptions',
      component: h(ManageFont, {
        editor,
        font_size: +settings.font_size || 15,
        font_family: settings.font_family || 'inter',
      }),
    },
    'Separator',
    ['Bullet List', 'Numbered List', 'Task List'],
    'Blockquote',
    'Code',
    'Separator',
    'Image',
    'Video',
    'Iframe',
    'Separator',
    TABLE_BUTTONS,
    'TableOfContents',
    'Separator',
    {
      label: 'Page Break',
      icon: LucideForm,
      action: (e) => e.commands.setPageBreak(),
    },
    {
      label: 'Custom Spacing',
      icon: LucideAlignVerticalSpacingAround,
      component: h(
        defineAsyncComponent(() => import('@/apps/writer/components/SpacingDialog.vue')),
        { settings, editor },
      ),
    },
    {
      icon: LucideSettings,
      label: 'Settings',
      action: openSettings,
    },
    {
      type: 'separator',
      condition: (e) => EXTRA_BUTTON_PREDICATES.some((fn) => fn(e)),
    },
    'DedentList',
    'IndentList',
  ]
}

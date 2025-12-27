<template>
  <nav
    id="navbar"
    ondragstart="return false;"
    ondrop="return false;"
    class="bg-surface-white border-b pr-5 py-2.5 h-12 flex items-center justify-between"
  >
    <a href="/writer">
      <div class="pl-2.5 pr-1">
        <WriterLogo class="size-7" />
      </div>
    </a>
    <slot name="breadcrumbs">
      <Breadcrumbs
        :items="formattedCrumbs"
        class="select-none truncate max-w-[80%]"
      />
    </slot>

    <div class="ml-auto flex items-center gap-3">
      <div id="navbar-content" class="flex gap-3" />
      <slot name="content" />
      <div v-if="document?.doc?.share_count" class="icon">
        <LucideGlobe2 v-if="document.doc.share_count === -2" class="size-4" />
        <LucideBuilding2
          v-else-if="document.doc.share_count === -1"
          class="size-4"
        />
        <LucideUsers v-else-if="document.doc.share_count > 0" class="size-4" />
      </div>
      <LucideStar
        v-if="document?.doc?.is_favourite"
        class="size-4 my-auto stroke-amber-500 fill-amber-500 mx-1.5"
      />
      <template v-if="!isLoggedIn">
        <Button variant="outline" @click="$router.push({ name: 'Login' })">
          Sign In
        </Button>
        <Button
          v-if="!isLoggedIn"
          class="hidden md:block"
          variant="solid"
          label="Try out Drive"
          @click="
            open('https://frappecloud.com/dashboard/signup?product=drive')
          "
        />
      </template>
      <Button
        v-else-if="$route.name === 'Home'"
        label="New"
        variant="solid"
        :icon-left="h(LucidePlus, { class: 'size-4' })"
        @click="
          createDocument.submit(null, {
            onSuccess: (d) =>
              $router.push({
                name: 'Document',
                params: { id: d.name },
              }),
          })
        "
      />
      <Dropdown
        v-else-if="fileActions.length"
        :options="fileActions"
        placement="right"
        :button="{
          variant: 'ghost',
          icon: LucideMoreHorizontal,
        }"
      />
    </div>
    <Dialogs v-model="dialog" :entities="document?.doc && [document.doc]" />
  </nav>
</template>
<script setup>
import { Button, Breadcrumbs, LoadingIndicator, Dropdown } from 'frappe-ui'
import { useStore } from 'vuex'
import emitter from '@/emitter'
import { ref, computed, inject, h, defineModel } from 'vue'
// import { entitiesDownload } from '@/utils/download'
import { createDocument } from '@/resources/'
import { exportBlog } from '@/utils/exports'
import Dialogs from '@/components/Dialogs.vue'
import { apps } from '@/resources/permissions'
import { dynamicList } from '@/utils/'

import { useRoute } from 'vue-router'
import LucideUsers from '~icons/lucide/users'
import LucideBuilding2 from '~icons/lucide/building-2'
import LucideStar from '~icons/lucide/star'
import LucideMoreHorizontal from '~icons/lucide/more-horizontal'
import LucideShare2 from '~icons/lucide/share-2'
import LucideDownload from '~icons/lucide/download'
import LucidePlus from '~icons/lucide/plus'
import LucideLink from '~icons/lucide/link'
import LucideArrowLeftRight from '~icons/lucide/arrow-left-right'
import LucideSquarePen from '~icons/lucide/square-pen'
import LucideInfo from '~icons/lucide/info'
import LucideRulerDimensionLine from '~icons/lucide/ruler-dimension-line'
import LucideView from '~icons/lucide/view'
import LucideListRestart from '~icons/lucide/list-restart'
import LucideHistory from '~icons/lucide/history'
import LucideLayoutTemplate from '~icons/lucide/layout-template'
import LucideMarkdown from '~icons/lucide/pilcrow'
import { downloadZippedHTML, downloadMD } from '@/utils'
import { downloadDocxFromHtml } from '../utils/docxexporter'
import { getLink } from '@/utils'
import WriterLogo from './WriterLogo.vue'

const store = useStore()
const open = (url) => {
  window.open(url, '_blank')
}

const props = defineProps({
  document: { type: Object, default: null },
  breadcrumbs: {
    default: [],
  },
})

const showVersions = defineModel('showVersions')
const showTemplates = defineModel('showTemplates')

const isLoggedIn = computed(() => store.getters.isLoggedIn)
const dialog = inject('dialog', ref(''))
const editor = inject('editor', null)

// Aliases for convenience in download functions
const entity = computed(() => props.document?.doc)
const settings = computed(() => props.document?.doc?.settings)

const formattedCrumbs = computed(() => {
  const ORIG = { label: 'Writer', route: '/' }
  if (!props.breadcrumbs.length) return [ORIG]
  return [
    ORIG,
    ...props.breadcrumbs.slice(1, -1).map((k) => ({
      ...k,
      route: true,
      onClick: (e) => {
        e.preventDefault()
        e.stopPropagation()
        window.location.replace('/drive/d/' + k.name)
      },
    })),
    {
      ...props.breadcrumbs[props.breadcrumbs.length - 1],
      onClick: () => emitter.emit('rename'),
    },
  ]
})

const fileActions = computed(() =>
  props.document?.doc?.settings
    ? [
        {
          group: true,
          hideLabel: true,
          items: [
            {
              label: __('Share'),
              icon: LucideShare2,
              onClick: () => {
                dialog.value = 's'
              },
              isEnabled: () => props.document.doc.share,
            },
            {
              label: __('Download'),
              icon: LucideDownload,
              isEnabled: () => props.document.doc.allow_download,
              onClick: () => emitter.emit('print-file'),
            },
            {
              label: __('Copy Link'),
              icon: LucideLink,
              onClick: () => getLink(props.document.doc),
            },
          ],
        },
        {
          group: true,
          hideLabel: true,
          items: [
            {
              label: __('Move'),
              icon: LucideArrowLeftRight,
              onClick: () => (dialog.value = 'm'),
              isEnabled: () => props.document.doc.write,
            },
            {
              label: __('Rename'),
              icon: LucideSquarePen,
              onClick: () => (dialog.value = 'rn'),
              isEnabled: () => props.document.doc.write,
            },
            {
              label: __('Show Info'),
              icon: LucideInfo,
              onClick: () => (dialog.value = 'i'),
              isEnabled: () =>
                !store.state.activeEntity || !store.state.showInfo,
            },
            {
              label: __('Favourite'),
              icon: LucideStar,
              onClick: () => {
                props.document.doc.is_favourite = true
                props.document.toggleFav.submit()
              },
              isEnabled: () => !props.document.doc.is_favourite,
            },
            {
              label: __('Unfavourite'),
              icon: LucideStar,
              color: 'stroke-amber-500 fill-amber-500',
              onClick: () => {
                props.document.doc.is_favourite = false
                props.document.toggleFav.submit()
              },
              isEnabled: () => props.document.doc.is_favourite,
            },
          ],
        },
        {
          group: true,
          hideLabel: true,
          items: dynamicList([
            {
              label: 'View',
              icon: LucideView,
              cond: props.document.doc.write,
              submenu: [
                {
                  label: 'Lock',
                  switch: true,
                  switchValue: props.document.doc.settings.lock,
                  icon: LucideLock,
                  onClick: (val) => {
                    props.document.doc.settings.lock = val
                    props.document.updateSettings.submit({
                      data: JSON.stringify(props.document.doc.settings),
                    })
                  },
                },
                {
                  label: 'Wide',
                  icon: LucideRulerDimensionLine,
                  switch: true,
                  switchValue: props.document.doc.settings.wide,
                  onClick: (val) => {
                    props.document.doc.settings.wide = val
                    props.document.updateSettings.submit({
                      data: JSON.stringify(props.document.doc.settings),
                    })
                  },
                },
              ],
            },
            {
              label: 'Export',
              icon: LucideDownload,
              submenu: [
                {
                  label: 'PDF',
                  icon: LucideFile,
                  onClick: () => {
                    emitter.emit('print-file')
                  },
                },
                {
                  label: 'DOCX',
                  icon: LucideFileText,
                  onClick: () => {
                    downloadDocxFromHtml(
                      editor.getHTML(),
                      `${entity.value.title}.docx`,
                      settings.value,
                    )
                  },
                },
                {
                  label: 'Folder',
                  icon: LucideFolderArchive,
                  onClick: () => {
                    downloadZippedHTML(
                      editor,
                      entity.value.title,
                      settings.value,
                    )
                  },
                },
                {
                  label: 'Markdown',
                  icon: LucideMarkdown,
                  onClick: () => downloadMD(editor, entity.value.title),
                },
                {
                  onClick: exportBlog,
                  label: 'Blog',
                  icon: LucideFileUser,
                  cond: apps.data && apps.data.find((k) => k.name === 'blog'),
                },
              ],
            },
            {
              icon: LucideHistory,
              label: 'Versions',
              cond: props.document.doc.write,
              onClick: () => (showVersions.value = true),
            },
            {
              icon: LucideLayoutTemplate,
              label: 'Templates',
              cond: props.document.doc.write,
              onClick: () => (showTemplates.value = true),
            },
          ]),
        },
        {
          group: true,
          hideLabel: true,
          items: [
            {
              onClick: () => clearCache(),
              label: 'Clear Cache',
              icon: LucideListRestart,
            },
            {
              label: __('Delete'),
              icon: LucideTrash,
              onClick: () => (dialog.value = 'remove'),
              isEnabled: () => props.document.doc.write,
              theme: 'red',
            },
          ],
        },
      ].map((k) => {
        return {
          ...k,
          items: k.items.filter((l) => !l.isEnabled || l.isEnabled()),
        }
      })
    : [],
)

// Utility functions for doc
const clearCache = () => {
  window.indexedDB.deleteDatabase('fdoc-' + props.document.doc.name)
  window.indexedDB.deleteDatabase('wdoc-comments-' + props.document.doc.name)
}
</script>

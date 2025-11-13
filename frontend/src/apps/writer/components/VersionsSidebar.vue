<template>
  <div
    class="bg-surface-gray-2 text-ink-gray-8 p-3 text-base flex justify-between items-center select-none"
  >
    <div class="flex flex-col gap-1">
      <div v-if="!versionPreview">
        <span class="text-ink-gray-6"
          >You are viewing the version history of</span
        >
        {{ title }}
      </div>
      <div v-else-if="versionPreview.manual">
        <span class="font-medium">{{ versionPreview.title }}</span>
      </div>
      <div v-else>
        This is a automatic snapshot of this document from
        {{ formatDate(versionPreview.title) }}.
      </div>
      <div class="text-xs text-ink-gray-5">
        Editing is disabled until you exit.
      </div>
    </div>
    <div class="flex gap-2">
      <Button
        variant="ghost"
        label="Exit"
        class="hover:!bg-surface-gray-2 hover:underline"
        @click="showVersions = false"
      />
      <Button
        variant="solid"
        label="Restore"
        @click="emitter.emit('restore-snapshot', versionPreview)"
      />
    </div>
  </div>
  <div class="flex h-full">
    <div class="self-stretch w-72 border-e h-full overflow-hidden relative">
      <!-- <h3
      class="ps-3 p-1.5 flex items-center justify-between text-xs text-ink-gray-9 font-medium mb-1"
    ></h3> -->
      <div class="flex flex-col items-center w-full">
        <Tabs
          v-model="tab"
          class="w-full"
          as="div"
          :tabs="[{ label: 'Automatic' }, { label: 'Manual' }]"
        />
        <Button
          :icon="LucideX"
          variant="ghost"
          class="absolute right-1 top-2"
          @click="showVersions = false"
        />
      </div>
      <div class="p-3.5 gap-4 flex flex-col h-full overflow-y-auto">
        <Button
          v-if="tab === 1"
          :icon="LucidePlus"
          class="absolute right-3 bottom-3"
          variant="outline"
          @click="
            () => {
              createDialog({
                title: 'Create Version',
                size: 'sm',
                component: h(NewVersionDialog),
                props: { editor },
              })
            }
          "
        />
        <div
          v-if="
            !Object.entries(groupedVersions).length ||
            !Object.entries(groupedVersions)[0][1].length
          "
          class="text-ink-gray-5 text-sm text-center mt-1"
        >
          None yet.
        </div>
        <div
          v-for="[title, group] in Object.entries(groupedVersions)"
          v-else
          :key="title"
          class="flex flex-col gap-0.5 justify-start bg-surface-white"
        >
          <div
            v-if="title !== 'Manual'"
            class="text-ink-gray-5 text-sm font-medium mb-1 my-2"
          >
            {{ title }}:
          </div>

          <Button
            v-for="version in group"
            :key="version.name"
            :variant="
              version.name === versionPreview?.name ? 'subtle' : 'ghost'
            "
            class="text-start text-sm py-4"
            :label="
              version.manual
                ? version.title
                : formatDate(version.title).slice(10)
            "
            @click="versionPreview = version"
          />
        </div>
      </div>
    </div>
    <div class="flex-1">
      <div
        v-if="!versionPreview"
        class="text-base border-b text-ink-gray-8 p-3 select-none"
      >
        This is the current version.
      </div>
      <TextEditor
        v-if="editor.getHTML"
        class="prose-sm prose-v2 md:min-w-[48rem] md:max-w-[48rem] mx-auto py-8"
        :extensions="COMMON_EXTENSIONS"
        :editable="false"
        :content="versionPreview?.snapshot || editor.getHTML()"
      >
        <template #editor="{ editor }">
          <EditorContent
            class="prose-sm prose-v2"
            :style="{
              fontFamily: `var(--font-${settings?.font_family})`,
              fontSize: `${settings?.font_size || 15}px`,
              lineHeight: settings?.line_height || 1.5,
            }"
            :editor="editor"
          />
        </template>
      </TextEditor>
    </div>
  </div>
</template>
<script setup>
import { COMMON_EXTENSIONS } from '@/utils'
import { toUint8Array } from 'js-base64'
import LucideX from '~icons/lucide/x'
import LucidePlus from '~icons/lucide/plus'
import { formatDate } from '@/utils/format'
import { computed, ref, h, watch } from 'vue'
import emitter from '@/emitter'
import { Tabs, TextEditor } from 'frappe-ui'
import { createDialog } from '@/utils/dialogs'
import NewVersionDialog from './NewVersionDialog.vue'
import { EditorContent } from '@tiptap/vue-3'

const props = defineProps({
  settings: Object,
  versions: Array,
  title: String,
  editor: Object,
})
const emit = defineEmits(['saveDocument', 'newVersion'])
const versionPreview = defineModel()
const showVersions = defineModel('showVersions')

const groupedVersions = computed(() => {
  if (tab.value === 0) {
    return props.versions.reduce((acc, version) => {
      if (version.manual) return acc
      const date = formatDate(version.title).slice(0, 8)
      if (!acc[date]) {
        acc[date] = []
      }
      acc[date].push(version)
      return acc
    }, {})
  } else {
    return { Manual: props.versions.filter((v) => v.manual) }
  }
})

const tab = ref(props.versions.filter((v) => v.manual).length ? 1 : 0)
watch(tab, () => (versionPreview.value = null))

emitter.on('restore-snapshot', (details) => {
  createDialog({
    title: 'Are you sure?',
    message: details.manual
      ? `You are restoring to a previous version: ${details.title}.`
      : `You are restoring the document to how it was at ${details.title}.`,
    actions: [
      {
        label: 'Confirm',
        variant: 'solid',
        onClick: () => {
          const view = props.editor.view
          view.dispatch(
            view.state.tr.setMeta(ySyncPluginKey, {
              snapshot: null,
              prevSnapshot: null,
            }),
          )
          showVersions.value = false
          emit('saveDocument')
        },
      },
    ],
  })
})
</script>
<style>
@import url('@/styles/fonts.css');
</style>

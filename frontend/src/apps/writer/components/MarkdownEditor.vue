<script setup>
import { provide, computed, ref, useTemplateRef } from 'vue'
import { TextEditor, TextEditorFixedMenu } from 'frappe-ui'
import { EditorContent } from '@tiptap/vue-3'
const props = defineProps({
  document: Object,
  settings: Object,
})

const content = ref(props.document.doc.file_content)

const editorEl = useTemplateRef('editorEl')
const editor = computed(() => editorEl.value?.editor)
provide('editor', editor)

const menuButtons = [
  'Paragraph',
  ['Heading 1', 'Heading 2', 'Heading 3'],
  'Separator',
  'Bold',
  'Italic',
  'Strikethrough',
  'Link',
  'Separator',
  ['Bullet List', 'Numbered List', 'Task List'],
  'Separator',
]
</script>
<template>
  <div class="flex flex-col w-full">
    <TextEditorFixedMenu
      v-if="editor"
      class="w-full max-w-[100vw] overflow-x-auto border-b border-outline-gray-modals justify-start md:justify-center py-1.5 shrink-0"
      :buttons="menuButtons"
    />
    <div class="overflow-y-auto">
      <div
        class="mx-auto cursor-text w-full flex justify-center h-full md:min-w-[48rem] md:max-w-[48rem] py-7"
      >
        <TextEditor ref="editorEl" :content>
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
  </div>
</template>

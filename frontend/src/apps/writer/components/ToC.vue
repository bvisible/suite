<template>
  <div
    v-if="editor"
    class="hidden md:block p-5 gap-2 sticky top-0 self-start bg-surface-white"
  >
    <Button
      v-if="tabs.length || anchors.length > 1"
      variant="ghost"
      :icon="
        h(show ? LucidePanelLeftClose : LucidePanelRightClose, {
          class: 'text-ink-gray-6',
        })
      "
      :tooltip="show ? 'Hide' : 'Table of Contents'"
      class="!w-5.5 !h-5.5 mb-2"
      @click="show = !show"
    />
    <div v-if="show" class="grow max-w-52 flex flex-col gap-0.5">
      <div v-if="tabs.length > 0" class="flex flex-col gap-0.5">
        <div v-for="tab in tabs" :key="tab.id">
          <TextInput
            v-if="editingTabId === tab.id"
            v-model="editingTabLabel"
            v-focus
            @keydown.enter="finishRenaming(false)"
            @keydown.esc="finishRenaming(true)"
            class="p-1"
          />
          <Button
            v-else
            :variant="tab.id === activeTabId ? 'subtle' : 'ghost'"
            class="w-full !justify-start"
            :class="tab.id === activeTabId && 'font-medium'"
            :label="tab.label"
            @click="editor.commands.changeTab(tab.id)"
            @dblclick="editor.isEditable && startRenaming(tab)"
          />
          <div
            v-if="tab.id === activeTabId"
            class="table-of-contents flex flex-col gap-0.5 ms-2 my-1"
          >
            <a
              v-for="anchor in currentTabAnchors"
              :href="'#' + anchor.id"
              class="link hover:bg-surface-gray-2 text-sm px-2 py-1 rounded-sm cursor-pointer truncate"
              :title="anchor.textContent"
              :data-item-index="anchor.itemIndex"
              @click.prevent="onAnchorClick(anchor.id)"
              :key="anchor.id"
              :class="{
                'is-active': anchor.isActive && !anchor.isScrolledOver,
                'text-ink-gray-5': anchor.isScrolledOver,
                'text-ink-gray-8': !anchor.isScrolledOver,
              }"
              :style="{ '--level': anchor.level - maxLevel }"
            >
              {{ anchor.textContent }}
            </a>
          </div>
        </div>
      </div>
      <div
        v-else-if="anchors.length > 1"
        class="table-of-contents flex flex-col gap-0.5"
      >
        <a
          v-for="anchor in anchors"
          :href="'#' + anchor.id"
          class="link hover:bg-surface-gray-2 text-sm px-2 py-1 rounded-sm cursor-pointer truncate"
          :title="anchor.textContent"
          :data-item-index="anchor.itemIndex"
          @click.prevent="onAnchorClick(anchor.id)"
          :key="anchor.id"
          :class="{
            'is-active': anchor.isActive && !anchor.isScrolledOver,
            'text-ink-gray-5': anchor.isScrolledOver,
            'text-ink-gray-8': !anchor.isScrolledOver,
          }"
          :style="{ '--level': anchor.level - maxLevel }"
        >
          {{ anchor.textContent }}
        </a>
      </div>
      <Button
        v-if="editor.isEditable"
        class="!justify-start text-xs opacity-50 hover:opacity-100 mt-2"
        :icon-left="h(LucidePlus, { class: 'size-4' })"
        :label="tabs.length ? 'Add' : 'Create tab'"
        variant="ghost"
        @click="
          tabs.length
            ? editor.commands.createTab({ label: 'Untitled' })
            : editor.commands.wrapInTab()
        "
      />
    </div>
  </div>
</template>

<script setup>
import { TextSelection } from '@tiptap/pm/state'
import LucidePlus from '~icons/lucide/Plus'
import LucidePanelLeftClose from '~icons/lucide/panel-left-close'
import LucidePanelRightClose from '~icons/lucide/table-of-contents'
import { ref, watch, computed, h } from 'vue'
import TextInput from 'frappe-ui/src/components/TextInput/TextInput.vue'

const props = defineProps({
  editor: Object,
  anchors: {
    type: Array,
    default: () => [],
  },
})

const show = ref(JSON.parse(localStorage.getItem('showToc') || true))
watch(show, (v) => localStorage.setItem('showToc', v))

// Get all tabs from the document
const tabs = computed(() => {
  if (!props.editor) return []
  const t = []
  props.editor.state.doc.descendants((node) => {
    if (node.type.name === 'tab') {
      t.push({ id: node.attrs.id, label: node.attrs.label })
    }
  })
  return t
})

// Get active tab ID
const activeTabId = computed(
  () => props.editor && props.editor.commands.getCurrentTab(),
)

// Filter anchors to only show those in the current tab
const currentTabAnchors = computed(() => {
  if (tabs.value.length === 0) return props.anchors
  if (!activeTabId.value) return props.anchors

  // Find the tab node position in the document
  let tabStart = null
  let tabEnd = null

  props.editor.state.doc.descendants((node, pos) => {
    if (node.type.name === 'tab' && node.attrs.id === activeTabId.value) {
      tabStart = pos
      tabEnd = pos + node.nodeSize
      return false
    }
  })

  if (tabStart === null) return []

  // Filter anchors that are within the active tab's position range
  return props.anchors.filter((anchor) => {
    const element = props.editor.view.dom.querySelector(
      `[data-toc-id="${anchor.id}"]`,
    )
    if (!element) return false

    const pos = props.editor.view.posAtDOM(element, 0)
    return pos >= tabStart && pos < tabEnd
  })
})

const maxLevel = computed(() =>
  currentTabAnchors.value.length
    ? Math.min(...currentTabAnchors.value.map((k) => k.level)) - 1
    : 0,
)

const onAnchorClick = (id) => {
  if (!props.editor) return
  const view = props.editor.view
  const tr = view.state.tr

  const element = view.dom.querySelector(`[data-toc-id="${id}"`)
  const pos = view.posAtDOM(element, 0)
  tr.setSelection(new TextSelection(tr.doc.resolve(pos)))
  props.editor.view.dispatch(tr)
  props.editor.view.focus()
  if (history.pushState) {
    history.pushState(null, null, `#${id}`)
  }

  const editorEl = document.querySelector('#editorScrollContainer')
  editorEl.scrollTo({
    top: element.offsetTop - 10,
    behavior: 'smooth',
  })
}

const editingTabId = ref(null)
const editingTabLabel = ref('')
const tabInput = ref(null)

const startRenaming = (tab) => {
  editingTabId.value = tab.id
  editingTabLabel.value = tab.label
}

const finishRenaming = (esc = false) => {
  if (!esc && editingTabId.value && editingTabLabel.value.trim()) {
    props.editor.commands.renameTab(
      editingTabId.value,
      editingTabLabel.value.trim(),
    )
  }
  editingTabId.value = null
  editingTabLabel.value = ''
}
</script>

<style scoped>
.table-of-contents {
  overflow: auto;
  text-decoration: none;
}

.table-of-contents a {
  text-decoration: none;

  &::before {
    content: '';
  }
}

.table-of-contents .link {
  border-radius: 0.25rem;
  margin-left: calc(0.875rem * (var(--level) - 1));
  transition: all 0.2s cubic-bezier(0.65, 0.05, 0.36, 1);
}
</style>

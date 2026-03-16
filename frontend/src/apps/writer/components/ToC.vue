<template>
  <div
    v-if="editor"
    class="px-2.5 gap-2 hidden md:block sticky top-0 self-start h-screen"
    :class="show && 'border-r border-outline-gray-2'"
  >
    <div class="pt-3" v-if="(tabs.length || anchors.length > 1) && !show">
      <Button
        variant="ghost"
        :icon="
          h(show ? LucidePanelLeftClose : LucideTableOfContents, {
            class: 'text-ink-gray-6',
          })
        "
        :tooltip="show ? 'Hide' : 'Table of Contents'"
        @click="show = !show"
      />
    </div>
    <div v-if="show" class="grow flex flex-col gap-0.5">
      <div
        v-if="tabs.length > 0"
        class="flex flex-col gap-0.5 mb-2"
        @drop.prevent="onDrop"
      >
        <div class="flex justify-between items-center ps-2 pr-1 pt-3 pb-1">
          <span class="text-base font-medium text-ink-gray-8"
            >Table of Contents</span
          >
          <Button
            :icon="LucideLeftClose"
            variant="ghost"
            @click="show = !show"
            :tooltip="show ? 'Hide' : 'Table of Contents'"
          />
        </div>
        <div
          v-for="(tab, index) in tabs"
          :key="tab.id"
          :class="[
            'relative transition-all duration-200',
            dragState.isDragging &&
              dragState.draggedId === tab.id &&
              'opacity-0',
          ]"
          @dragover.prevent="onDragOver($event, index)"
        >
          <div
            v-if="
              dragState.isDragging &&
              dragState.dropIndex === index &&
              dragState.dropIndex !== dragState.draggedIndex &&
              dragState.dropIndex !== dragState.draggedIndex + 1
            "
            class="h-8 my-0.5 border border-dashed rounded-sm mx-2"
          />
          <div
            v-if="editingTabId === tab.id"
            class="flex items-center"
            v-on-outside-click="() => finishRenaming(true)"
          >
            <TextInput
              v-model="editingTabLabel"
              v-focus
              @keydown.enter="finishRenaming(false)"
              @keydown.esc="finishRenaming(true)"
              class="p-1"
            />
            <Button
              variant="outline"
              :icon="LucideTrash"
              @click="editor.commands.deleteTab(tab.id)"
            />
          </div>
          <Button
            v-else
            variant="ghost"
            class="w-full !text-ink-gray-5 !justify-start cursor-grab active:cursor-grabbing"
            :class="tab.id === activeTabId && 'font-medium !text-ink-gray-8'"
            :label="tab.label"
            :icon-left="h(LucideFileText, { class: 'size-4' })"
            @click="tab.id !== activeTabId && editor.commands.changeTab(tab.id)"
            @dblclick.stop="editor.isEditable && startRenaming(tab)"
            :draggable="editor.isEditable"
            @dragstart="onDragStart($event, tab, index)"
            @dragend.prevent="onDragEnd"
          />

          <div
            v-if="tab.id === activeTabId && currentTabAnchors.length"
            class="table-of-contents flex flex-col gap-0.5 ms-6 my-1"
          >
            <div v-for="anchor in currentTabAnchors" class="flex">
              <a
                :href="'#' + anchor.id"
                class="link text-ink-gray-5 hover:bg-surface-gray-2 text-sm px-2 py-1 rounded-sm cursor-pointer truncate grow"
                :title="anchor.textContent"
                :data-item-index="anchor.itemIndex"
                @click.prevent="onAnchorClick(anchor.id)"
                :key="anchor.id"
                :class="
                  anchor.isActive &&
                  'text-ink-gray-8 bg-surface-gray-3 hover:bg-surface-gray-4'
                "
                :style="{ '--level': anchor.level - maxLevel }"
              >
                {{ anchor.textContent }}
              </a>
            </div>
          </div>
        </div>
        <div
          v-if="dragState.isDragging && dragState.dropIndex === tabs.length"
          @dragover.prevent
          class="h-8 my-0.5 border border-dashed rounded-sm mx-2"
        />
      </div>
      <div
        v-else-if="anchors.length > 1"
        class="table-of-contents flex flex-col gap-0.5 mb-2"
      >
        <div v-for="anchor in anchors" class="flex">
          <a
            :href="'#' + anchor.id"
            class="link text-ink-gray-5 hover:bg-surface-gray-2 text-sm px-2 py-1 rounded-sm cursor-pointer truncate grow"
            :title="anchor.textContent"
            :data-item-index="anchor.itemIndex"
            @click.prevent="onAnchorClick(anchor.id)"
            :key="anchor.id"
            :class="anchor.isActive && 'text-ink-gray-8'"
            :style="{ '--level': anchor.level - maxLevel }"
          >
            {{ anchor.textContent }}
          </a>
        </div>
      </div>
      <Button
        v-if="editor.isEditable"
        class="!justify-start text-xs opacity-50 hover:opacity-100"
        :icon-left="h(LucidePlus, { class: 'size-4' })"
        :label="tabs.length ? 'Add tab' : 'Create tab'"
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
import LucideFileText from '~icons/lucide/file-text'
import LucideTableOfContents from '~icons/lucide/table-of-contents'
import LucideTrash from '~icons/lucide/trash'
import LucideLeftClose from '~icons/lucide/panel-left-close'
import { ref, watch, computed, h, onMounted, onBeforeUnmount } from 'vue'
import { TextInput } from 'frappe-ui'

const props = defineProps({
  editor: Object,
  anchors: {
    type: Array,
    default: () => [],
  },
})

// const show = ref(JSON.parse(localStorage.getItem('showToc') || true))
const show = ref(true)
watch(show, (v) => localStorage.setItem('showToc', v))

// Get all tabs from the document
const tabs = computed(() => {
  const t = []
  props.editor.state.doc.descendants((node) => {
    if (node.type.name === 'tab') {
      t.push({ id: node.attrs.id, label: node.attrs.label })
    }
  })
  return t
})

// Get active tab ID
const activeTabId = ref()
onMounted(() => {
  const handleTabChange = (e) => {
    activeTabId.value = e.detail.tabId
  }

  props.editor.view.dom.addEventListener('tab-changed', handleTabChange)
  onBeforeUnmount(() => {
    props.editor.view.dom.removeEventListener('tab-changed', handleTabChange)
  })
})

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

  const element = view.dom.querySelector(`[data-toc-id="${id}"]`)
  const pos = view.posAtDOM(element, 0)
  tr.setSelection(new TextSelection(tr.doc.resolve(pos)))
  props.editor.view.dispatch(tr)
  props.editor.view.focus()
  if (history.pushState) {
    history.pushState(null, null, `#${id}`)
  }

  const editorEl = document.querySelector('#editorScrollContainer')
  editorEl.scrollTo({
    top: element.offsetTop,
  })
}

const editingTabId = ref(null)
const editingTabLabel = ref('')

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
  props.editor.commands.focus()
}

const tabEvent = ref(null)
const selectedTab = ref(null)

// Drag and drop state
const dragState = ref({
  isDragging: false,
  draggedId: null,
  draggedIndex: null,
  dropIndex: null,
})

let ghostElement = null

const onDragStart = (event, tab, index) => {
  if (!props.editor.isEditable) return

  dragState.value.isDragging = true
  dragState.value.draggedId = tab.id
  dragState.value.draggedIndex = index

  // Create ghost element
  const target = event.target.closest('button')
  ghostElement = target.cloneNode(true)
  ghostElement.style.position = 'fixed'
  ghostElement.style.pointerEvents = 'none'
  ghostElement.style.opacity = '0.6'
  document.body.appendChild(ghostElement)

  event.dataTransfer.setDragImage(ghostElement, 0, 0)
  event.dataTransfer.effectAllowed = 'move'
}

const onDragOver = (event, index) => {
  if (!dragState.value.isDragging) return

  const rect = event.currentTarget.getBoundingClientRect()
  const midpoint = rect.top + rect.height / 2

  // Determine if we should drop before or after this element
  if (event.clientY < midpoint) {
    dragState.value.dropIndex = index
  } else {
    dragState.value.dropIndex = index + 1
  }
}

const onDrop = () => {
  if (!dragState.value.isDragging) return

  const fromIndex = dragState.value.draggedIndex
  const toIndex = dragState.value.dropIndex

  // Only reorder if position actually changed
  if (fromIndex !== toIndex && toIndex !== fromIndex + 1) {
    const adjustedToIndex = toIndex > fromIndex ? toIndex - 1 : toIndex
    props.editor.commands.reorderTab(dragState.value.draggedId, adjustedToIndex)
  }

  onDragEnd()
}

const onDragEnd = (event) => {
  if (event?.target?._cleanupDrag) {
    event.target._cleanupDrag()
  }

  if (ghostElement) {
    document.body.removeChild(ghostElement)
    ghostElement = null
  }

  dragState.value.isDragging = false
  dragState.value.draggedId = null
  dragState.value.draggedIndex = null
  dragState.value.dropIndex = null
}

const activeAnchorId = computed(() => {
  if (!currentTabAnchors.value.length) return null
  let activeId = null
  const curPos = props.editor.isFocused
    ? props.editor.view.domAtPos(props.editor.state.selection.from).top
    : props.editor.storage.tableOfContents?.scrollPosition + 25

  for (let i = 0; i < currentTabAnchors.value.length; i++) {
    const anchor = currentTabAnchors.value[i]

    if (anchor.dom.offsetTop <= curPos) {
      activeId = anchor.id
    } else {
      break
    }
  }

  // If no anchor is active yet, use the first one
  return activeId
})
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

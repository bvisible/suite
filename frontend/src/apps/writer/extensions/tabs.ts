import { Extension } from '@tiptap/core'
import { Node } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import TabView from './components/TabView.vue'
import { v4 } from 'uuid'

export const Tab = Node.create({
  name: 'tab',
  group: 'block',
  content: 'block+',

  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-tab-id'),
        renderHTML: (attrs) => (attrs.id ? { 'data-tab-id': attrs.id } : {}),
      },
      label: {
        default: 'Untitled',
        parseHTML: (el) => el.getAttribute('data-tab-label'),
        renderHTML: (attrs) => ({ 'data-tab-label': attrs.label }),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-tab-id]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', HTMLAttributes, 0]
  },
})

// Extension for tab management
export const TabsExtension = Extension.create({
  name: 'tabs',

  addStorage() {
    return {
      activeTabId: null,
    }
  },

  onCreate() {
    // Select first tab on mount
    const { doc } = this.editor.state
    let set = false
    doc.descendants((node) => {
      if (!set && node.type.name === 'tab') {
        this.storage.activeTabId = node.attrs.id
        set = true
      }
    })
  },

  addCommands() {
    return {
      changeTab: (tabId: string) => () => {
        this.storage.activeTabId = tabId
        this.editor.view.dispatch(this.editor.state.tr)
        return true
      },
      wrapInTab:
        (attrs: { id: string; label: string }) =>
        ({ tr, dispatch }) => {
          if (dispatch) {
            if (!attrs.id) attrs.id = v4()
            const tabType = this.editor.schema.nodes.tab
            tr.replaceWith(
              0,
              tr.doc.content.size,
              tabType.create(attrs, tr.doc.content),
            )
            this.storage.activeTabId = attrs.id
            dispatch(tr)
            return true
          }
        },
    }
  },

  addNodeView() {
    return VueNodeViewRenderer(TabView, {
      props: { activeId: () => this.options.activeId },
    })
  },
})

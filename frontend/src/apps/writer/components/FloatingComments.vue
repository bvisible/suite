<template>
  <div
    ref="scrollContainer"
    class="relative hidden md:flex flex-col gap-8 justify-start self-stretch px-5 bg-surface-white"
  >
    <slot />
    <template
      v-if="showComments"
      v-for="comment in filteredComments"
      :key="comment.id"
    >
      <div
        :id="'comment-' + comment.id"
        :ref="
          (el) => {
            if (el) commentRefs[comment.id] = el
            else delete commentRefs[comment.id]
          }
        "
        v-on-outside-click="
          (e) => {
            if (
              activeComment === comment.id &&
              !e.target.getAttribute('data-comment-name') &&
              e.target.nodeName === 'DIV' &&
              !comment.new &&
              !e.target.classList?.contains?.('replies-count')
            )
              activeComment = null
          }
        "
        class="absolute rounded shadow w-52 md:w-72 comment-group scroll-m-24 bg-surface-white opacity-0 pointer-events-none transition-[top] duration-100 ease-in-out"
        :class="[
          activeComment === comment.id && 'shadow-xl ',
          comment.top && 'opacity-100 pointer-events-auto',
        ]"
        :style="`top: ${comment.top}px;`"
        @click="activeComment = comment.id"
      >
        <div
          v-show="
            activeComment === comment.id &&
            $store.state.user.id !== 'Guest' &&
            !comment.new &&
            (comment.owner == $store.state.user.id || document.doc.write)
          "
          class="p-1.5 text-sm flex gap-1 border-b text-ink-gray-9"
          :class="comment.loading && !comment.edit && 'opacity-70'"
        >
          <Button
            v-if="
              !comment.resolved &&
              (comment.owner == $store.state.user.id || document.doc.write)
            "
            :disabled="comment.loading"
            variant="ghost"
            class="!h-5 !text-xs !px-1.5 !rounded-sm"
            @click="resolve(comment)"
          >
            <template #prefix>
              <LucideCheck class="size-3.5" />
            </template>
            Resolve
          </Button>
          <Button
            v-if="
              comment.resolved &&
              (comment.owner == $store.state.user.id || document.doc.write)
            "
            :disabled="comment.loading"
            variant="ghost"
            class="!h-5 !text-xs !px-1.5 !rounded-sm"
            @click="resolve(comment, false)"
          >
            <template #prefix>
              <LucideMessageCircleCode class="size-3.5" />
            </template>
            Unresolve
          </Button>
          <Button
            v-if="
              comment.owner == $store.state.user.id ||
              (comment.owner === 'Guest' && document.doc.write)
            "
            :disabled="comment.loading"
            variant="ghost"
            class="!h-5 !text-xs !px-1.5 !rounded-sm"
            @click="removeComment(comment.id, true)"
          >
            <template #prefix>
              <LucideX class="size-3.5" />
            </template>
            Delete
          </Button>
        </div>
        <div
          class="p-3"
          :class="
            activeComment !== comment.id &&
            comment.replies.length > 0 &&
            'pb-1.5'
          "
        >
          <blockquote
            v-if="comment.detached"
            class="text-xs text-ink-gray-8 mb-4"
          >
            Replying to:
            <span class="text-ink-gray-5 italic">{{ comment.anchorText }}</span>
          </blockquote>
          <div class="flex flex-col gap-5">
            <div
              v-for="(reply, index) in activeComment === comment.id
                ? [
                    comment,
                    ...comment.replies.toSorted((a, b) =>
                      new Date(a.creation) > new Date(b.creation) ? 1 : -1,
                    ),
                  ]
                : [comment]"
              :key="reply.name || reply.id"
              class="group flex-grow flex gap-3"
              :class="reply.loading && !reply.edit && 'opacity-70'"
            >
              <div class="w-8 flex justify-center">
                <Avatar
                  size="xl"
                  class="bg-surface-white"
                  :label="$user(reply.owner)?.full_name || reply.owner"
                  :image="$user(reply.owner)?.user_image"
                />
              </div>
              <div
                class="grow flex flex-col min-w-0"
                :class="reply.edit && 'gap-1'"
              >
                <div
                  class="w-full flex justify-between items-start label-group gap-1 text-sm"
                >
                  <div class="flex gap-1">
                    <label
                      class="font-medium text-ink-gray-8 max-w-[70%] truncate"
                      >{{ $user(reply.owner)?.full_name || reply.owner }}</label
                    >

                    <label
                      class="text-ink-gray-6 truncate"
                      :title="new Date(reply.creation)"
                    >
                      &#183;
                      {{ formatDateOrTime(reply.creation) }}</label
                    >
                  </div>
                  <Dropdown
                    class="ml-auto opacity-0"
                    :class="
                      activeComment === comment.id &&
                      !reply.edit &&
                      !reply.resolved &&
                      comment.owner == $store.state.user.id &&
                      'opacity-100'
                    "
                    :options="
                      dynamicList([
                        {
                          label: 'Edit',
                          onClick: () => (reply.edit = true),
                          cond: comment.owner == $store.state.user.id,
                        },
                        {
                          label: 'Delete',
                          onClick: () => removeReply(comment.id, reply.id),
                          cond:
                            comment.owner == $store.state.user.id &&
                            index !== 0,
                        },
                      ])
                    "
                  >
                    <Button
                      :disabled="
                        activeComment !== comment.id ||
                        reply.edit ||
                        reply.resolved
                      "
                      class="!h-5 !text-xs !px-1.5 !rounded-sm opacity-0"
                      :class="
                        activeComment === comment.id &&
                        !reply.edit &&
                        !reply.resolved &&
                        comment.owner == $store.state.user.id &&
                        'opacity-100'
                      "
                      variant="ghost"
                      :icon="h(LucideMoreVertical, { class: 'size-3' })"
                      @click="triggerRoot"
                    />
                  </Dropdown>
                  <LucideBadgeCheck
                    v-if="comment.resolved"
                    class="text-ink-gray-6 size-4"
                  />
                </div>
                <div class="comment-content text-sm">
                  <CommentEditor
                    v-model="commentContents[reply.id]"
                    placeholder="Edit"
                    :disabled="
                      isEmpty(commentContents[reply.id]) ||
                      commentContents[reply.id] == reply.text
                    "
                    :editable="!!(reply.edit || reply.new)"
                    :content="reply.text"
                    @change="setCommentHeights"
                    @submit="
                      (editor) => {
                        updateComment(reply, comment, editor)
                      }
                    "
                    @cancel="
                      (editor) => {
                        if (reply.new) {
                          removeComment(reply.id)
                        } else {
                          editor.commands.setContent(reply.text)
                          reply.edit = false
                        }
                      }
                    "
                  />
                </div>
              </div>
            </div>

            <div
              v-show="
                activeComment === comment.id &&
                !(comment.edit || comment.new) &&
                !comment.resolved
              "
              class="flex gap-3"
            >
              <Avatar
                size="xl"
                class="self-center"
                :label="
                  $user($store.state.user.id)?.full_name || $store.state.user.id
                "
                :image="$user($store.state.user.id)?.user_image"
              />

              <CommentEditor
                v-model="newReplies[comment.id]"
                placeholder="Reply"
                :is-empty="isEmpty(newReplies[comment.id])"
                @change="setCommentHeights"
                @submit="(editor) => newReply(comment, editor)"
                @cancel="
                  (editor) => {
                    newReplies[comment.id] = ''
                    editor.commands.setContent('')
                    editor.commands.blur()
                  }
                "
              />
            </div>
          </div>
        </div>
        <div
          v-if="activeComment !== comment.id && comment.replies.length > 0"
          class="replies-count text-ink-gray-6 font-base text-xs p-3 pt-0"
        >
          {{ comment.replies.length }}
          {{ comment.replies.length === 1 ? 'reply' : 'replies' }}
        </div>
      </div>
    </template>
  </div>
</template>
<script setup>
import {
  computed,
  reactive,
  watch,
  onMounted,
  ref,
  h,
  onBeforeUnmount,
  nextTick,
} from 'vue'
import { Avatar, Button, Dropdown } from 'frappe-ui'
import { formatDate } from '@/utils/format'
import { dynamicList } from '@/utils/'
import { v4 } from 'uuid'
import { useDebounceFn, useEventListener } from '@vueuse/core'
import LucideX from '~icons/lucide/x'
import LucideMoreVertical from '~icons/lucide/more-vertical'
import store from '@/store'
import CommentEditor from './CommentEditor.vue'
import { rebuild, getEditorPos } from '@/extensions/comments'

const props = defineProps({
  document: Object,
  editor: Object,
  yComments: Object,
  showComments: Boolean,
  showResolved: Boolean,
})
const emit = defineEmits(['save'])

const activeComment = defineModel('activeComment')
const scrollContainer = ref('scrollContainer')

const newReplies = reactive({})
const commentRefs = reactive({})
const commentContents = reactive({})

// for old schema, where comment positions isn't in the map
const commentPositions = computed(() => {
  const positions = new Map()

  props.editor.state.doc.descendants((node, pos) => {
    node.marks.forEach((mark) => {
      if (mark.type.name === 'comment' && mark.attrs.commentId) {
        if (!positions.has(mark.attrs.commentId)) {
          positions.set(mark.attrs.commentId, pos)
        }
      }
    })
  })
  return positions
})

function useYMapReactive(yMap) {
  const local = ref([])

  const update = () => {
    const arr = []
    yMap.forEach((v) => {
      let pos
      if (!v.anchor?.from) pos = commentPositions.value.get(v.id) ?? 0
      else pos = getEditorPos(v.anchor.from, props.editor)
      arr.push({ ...v, pos })
    })
    local.value = arr.sort((a, b) => a.pos - b.pos)
  }

  update()
  yMap.observe(update)

  onBeforeUnmount(() => yMap.unobserve(update))

  return local
}
const comments = useYMapReactive(props.yComments)

const filteredComments = computed(() => {
  const filtered = props.showResolved
    ? comments.value
    : comments.value.filter((k) => !k.resolved)
  return filtered
})
watch(
  () => props.showResolved,
  () => rebuild(props.editor),
)

watch(activeComment, (val) => {
  setCommentHeights()
})

const sanitize = (comment) => {
  delete comment.new
  comment.edit = false
  const obj = { ...comment }
  delete obj.edit
  delete obj.new
  delete obj.top
  return obj
}

const updateComment = (comment, thread, editor) => {
  comment.text = commentContents[comment.id]
  comment.edit = false
  comment.mentions = editor.commands.getMentions()

  // // Prompt to share for users without access.
  // const usersMentioned = comment.mentions.filter((k) => k.id)

  // if (usersMentioned.length)
  //   toast.info('Share with the tagged people?', {
  //     action: {
  //       label: 'Go',
  //       onClick: () => emitter.emit('share', usersMentioned),
  //     },
  //   })
  if (comment.id === thread.id) {
    props.yComments.set(comment.id, sanitize(comment))
  } else {
    thread.replies = thread.replies.map((r) =>
      r.id === comment.id ? sanitize(comment) : r,
    )
    props.yComments.set(thread.id, sanitize(thread))
  }
  emit('save')
}

const newReply = (comment, editor) => {
  const id = v4()
  const reply = {
    id,
    text: newReplies[comment.id],
    owner: store.state.user.id,
    creation: Date.now(),
    mentions: editor.commands.getMentions(),
  }
  comment.replies.push(reply)
  props.yComments.set(comment.id, comment)

  editor.commands.setContent('')
  setCommentHeights()
  emit('save')
}

const removeReply = (commentId, replyId) => {
  const comment = comments.value.find((c) => c.id === commentId)
  if (!comment) return

  const updatedReplies = comment.replies.filter((r) => r.id !== replyId)
  const updatedComment = { ...comment, replies: updatedReplies }
  props.yComments.set(commentId, updatedComment)

  setCommentHeights()
  emit('save')
}

const removeComment = (commentId) => {
  props.yComments.delete(commentId)
  setCommentHeights()
  emit('save')
  rebuild(props.editor)
}

const resolve = (comment, value = true) => {
  const updatedComment = { ...comment, resolved: value }
  props.yComments.set(comment.id, sanitize(updatedComment))
  emit('save')
}

const isEmpty = (editorContent) => {
  return (
    !editorContent ||
    !editorContent.length ||
    editorContent.replace(/\s/g, '') == '<p></p>'
  )
}

const formatDateOrTime = (datetimeNum) => {
  const now = new Date()
  const datetime = new Date(datetimeNum)
  const isToday =
    datetime.getDate() === now.getDate() &&
    datetime.getMonth() === now.getMonth() &&
    datetime.getFullYear() === now.getFullYear()
  const [dateStr, timeStr] = formatDate(datetime).split(', ')
  return isToday ? timeStr : dateStr
}

const setCommentHeights = useDebounceFn(() => {
  let lastBottom = 0
  nextTick(() => {
    for (const comment of filteredComments.value) {
      try {
        const containerTop = scrollContainer.value.getBoundingClientRect().top
        const el =
          document.querySelector(`[data-comment-name="${comment.id}"]`) ||
          document.querySelector(`[data-comment-id="${comment.id}"]`)
        let anchorTop
        if (!el && comment.anchorText) {
          comment.detached = 1
          anchorTop = 48
        } else {
          anchorTop = el.getBoundingClientRect().top - containerTop
          comment.detached = 0
        }
        const adjustedTop = Math.max(anchorTop, lastBottom)
        comment.top = adjustedTop
        if (adjustedTop)
          lastBottom = adjustedTop + commentRefs[comment.id].offsetHeight + 12
      } catch (e) {
        console.log(e)
      }
    }
  })
}, 100)

onMounted(() => {
  setCommentHeights()
  const onTabChange = () => {
    activeComment.value = null
    setCommentHeights()
  }
  props.editor.view.dom.addEventListener('tab-changed', onTabChange)
  onBeforeUnmount(() => {
    try {
      const dom = props.editor?.view?.dom
      dom.removeEventListener('tab-changed', onTabChange)
    } catch {}
  })
})

watch(() => filteredComments.value.length, setCommentHeights)
useEventListener(window, 'resize', setCommentHeights)

props.editor.on('update', () => {
  setCommentHeights()
})

const purgeNewEmptyComments = () => {
  for (const comment of comments.value)
    if (comment.new) removeComment(comment.id, true)
}

onBeforeUnmount(purgeNewEmptyComments)
useEventListener(window, 'beforeunload', purgeNewEmptyComments)
</script>

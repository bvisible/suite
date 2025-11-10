<template>
  <nav
    id="navbar"
    ondragstart="return false;"
    ondrop="return false;"
    class="bg-surface-white border-b px-5 py-2.5 h-12 flex justify-between"
  >
    <slot name="breadcrumbs">
      <Breadcrumbs
        :items="formattedCrumbs"
        class="select-none truncate max-w-[80%]"
      />
    </slot>

    <div class="ml-auto flex items-center gap-2">
      <slot name="content" />
      <div class="icon mr-2">
        <LucideGlobe2 v-if="rootEntity?.share_count === -2" class="size-4" />
        <LucideBuilding2
          v-else-if="rootEntity?.share_count === -1"
          class="size-4"
        />
        <LucideUsers v-else-if="rootEntity?.share_count > 0" class="size-4" />
      </div>
      <LucideStar
        v-if="rootEntity?.is_favourite"
        class="size-4 my-auto stroke-amber-500 fill-amber-500"
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
        v-else-if="defaultActions"
        :options="defaultActions"
        placement="right"
        :button="{
          variant: 'ghost',
          icon: LucideMoreHorizontal,
        }"
      />
    </div>
    <Dialogs
      v-model="dialog"
      :entities="entities.length ? entities : rootEntity ? [rootEntity] : []"
    />
  </nav>
</template>
<script setup>
import { Button, Breadcrumbs, LoadingIndicator, Dropdown } from 'frappe-ui'
import { useStore } from 'vuex'
import emitter from '@/emitter'
import { ref, computed, inject, h } from 'vue'
// import { entitiesDownload } from '@/utils/download'
import { createDocument } from '@/resources/'
import Dialogs from '@/components/Dialogs.vue'
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

const store = useStore()
const open = (url) => {
  window.open(url, '_blank')
}

const props = defineProps({
  rootEntity: { type: Object, default: null },
  breadcrumbs: {
    default: [],
  },
  actions: { type: Array, default: [] },
  // Used to pass into dialogs
  entities: {
    type: Array,
    default: () => [],
  },
})

const isLoggedIn = computed(() => store.getters.isLoggedIn)
const dialog = inject('dialog', ref(''))

const formattedCrumbs = computed(() => {
  const ORIG = { label: 'Writer', route: '/' }
  if (!props.breadcrumbs.length) return [ORIG]
  return [
    ORIG,
    ...props.breadcrumbs
      .slice(1, -1)
      .map((k) => ({ ...k, route: '/drive/d/' + k.name })),
    ...props.breadcrumbs.slice(-1),
  ]
})

const defaultActions = computed(() => {
  if (!props.rootEntity?.title) return
  let actions = []
  if (props.actions) {
    if (props.actions[0] === 'extend') actions = props.actions.slice(1)
    else return props.actions
  }
  return [
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
          isEnabled: () => props.rootEntity.share,
        },
        {
          label: __('Download'),
          icon: LucideDownload,
          isEnabled: () => props.rootEntity.allow_download,
          onClick: () =>
            entitiesDownload(route.params.team, [props.rootEntity]),
        },
        {
          label: __('Copy Link'),
          icon: LucideLink,
          onClick: () => getLink(props.rootEntity),
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
          isEnabled: () => props.rootEntity.write,
        },
        {
          label: __('Rename'),
          icon: LucideSquarePen,
          onClick: () => (dialog.value = 'rn'),
          isEnabled: () => props.rootEntity.write,
        },
        {
          label: __('Show Info'),
          icon: LucideInfo,
          onClick: () => (dialog.value = 'i'),
          isEnabled: () => !store.state.activeEntity || !store.state.showInfo,
        },
        {
          label: __('Favourite'),
          icon: LucideStar,
          onClick: () => {
            props.rootEntity.is_favourite = true
            toggleFav.submit({
              entities: [{ name: props.rootEntity.name, is_favourite: false }],
            })
          },
          isEnabled: () => !props.rootEntity.is_favourite,
        },
        {
          label: __('Unfavourite'),
          icon: LucideStar,
          color: 'stroke-amber-500 fill-amber-500',
          onClick: () => {
            props.rootEntity.is_favourite = false
            toggleFav.submit({
              entities: [{ name: props.rootEntity.name, is_favourite: false }],
            })
          },
          isEnabled: () => props.rootEntity.is_favourite,
        },
      ],
    },
    {
      group: true,
      hideLabel: true,
      items: [
        {
          label: __('Delete'),
          icon: LucideTrash,
          onClick: () => (dialog.value = 'remove'),
          isEnabled: () => props.rootEntity.write,
          theme: 'red',
        },
      ],
    },
    ...actions,
  ].map((k) => {
    return { ...k, items: k.items.filter((l) => !l.isEnabled || l.isEnabled()) }
  })
})
</script>

<template>
  <nav
    id="navbar"
    ondragstart="return false;"
    ondrop="return false;"
    class="bg-surface-white border-b px-5 py-2.5 h-12 flex justify-between"
  >
    <slot name="breadcrumbs">
      <Breadcrumbs :items="formattedCrumbs" class="select-none truncate max-w-[80%]" />
    </slot>

    <div class="ml-auto flex gap-2">
      <slot name="content" />
      <div class="icon mr-2">
        <LucideGlobe2 v-if="rootEntity?.share_count === -2" class="size-4" />
        <LucideBuilding2 v-else-if="rootEntity?.share_count === -1" class="size-4" />
        <LucideUsers v-else-if="rootEntity?.share_count > 0" class="size-4" />
      </div>
      <LucideStar
        v-if="rootEntity?.is_favourite"
        class="size-4 my-auto stroke-amber-500 fill-amber-500"
      />
      <template v-if="!isLoggedIn">
        <Button variant="outline" @click="$router.push({ name: 'Login' })"> Sign In </Button>
        <Button
          v-if="!isLoggedIn"
          class="hidden md:block"
          variant="solid"
          label="Try out Drive"
          @click="open('https://frappecloud.com/dashboard/signup?product=drive')"
        />
      </template>
      <Button
        v-else-if="$route.name === 'Home'"
        label="Create"
        variant="solid"
        :icon-left="h(LucidePlus, { class: 'size-4' })"
        @click="createDocument"
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
      <Button
        v-if="button"
        :disabled="!button.entities.data?.length"
        :theme="button.theme || 'gray'"
        @click="dialog = 'cta-' + $route.name.toLowerCase()"
      >
        <template #prefix>
          <component :is="button.icon" class="size-4" />
        </template>
        {{ button.label }}
      </Button>
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
import { entitiesDownload } from '@/utils/download'
import { getRecents, getTrash, toggleFav, createDocument } from '@/resources/files'
import { apps } from '@/resources/permissions'
import { useRoute } from 'vue-router'
import { getLink, dynamicList } from '@/utils'
import LucideClock from '~icons/lucide/clock'
import LucideHome from '~icons/lucide/home'
import LucideTrash from '~icons/lucide/trash'
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
const route = useRoute()
const open = (url) => {
  window.open(url, '_blank')
}

const props = defineProps({
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
  return [ORIG, ...props.breadcrumbs.slice(1)]
})
</script>

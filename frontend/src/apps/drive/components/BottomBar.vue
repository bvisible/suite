<template>
  <MobileNav>
    <MobileNavItem
      v-for="tab in sidebarItems"
      :key="tab.label"
      :label="tab.label"
      :icon="tab.icon"
      :route="tab.route"
      :active="tab.highlight()"
    />
  </MobileNav>
</template>
<script>
import { MobileNav, MobileNavItem } from 'frappe-ui'
import LucideClock from '~icons/lucide/clock'
import LucideHome from '~icons/lucide/home'
import LucideStar from '~icons/lucide/star'
import LucideBuilding2 from '~icons/lucide/building-2'
import { getRootSection } from '@/apps/drive/data/breadcrumbs'
import { rootInfo } from '@/apps/drive/resources/files'

export default {
  name: 'BottomBar',
  components: { MobileNav, MobileNavItem },
  computed: {
    sidebarItems() {
      const first = getRootSection()
      //// Neoffice — the labels in the reader's language: a French phone read « Home · Recents · Everyone ·
      //// Favourites » (maintenance#1392). The desk's sidebar already says them through __().
      return [
        {
          label: __('Home'),
          route: { name: 'drive-Home' },
          icon: LucideHome,
          highlight: () => first.name === 'drive-Home',
        },
        {
          label: __('Recents'), //// Neoffice — the reader's language (#1392)
          route: { name: 'drive-Recents' },
          icon: LucideClock,
          highlight: () => first.name === 'drive-Recents',
        },
        {
          label: __('Everyone'), //// Neoffice — the reader's language (#1392)
          route: rootInfo.data
            ? { name: 'drive-Folder', params: { entityName: rootInfo.data.root } }
            : { name: 'drive-Home' },
          icon: LucideBuilding2,
          highlight: () => first.name === rootInfo.data?.root,
        },
        {
          label: __('Favourites'), //// Neoffice — the reader's language (#1392)
          route: { name: 'drive-Favourites' },
          icon: LucideStar,
          highlight: () => first.name === 'drive-Favourites',
        },
      ]
    },
  },
}
</script>

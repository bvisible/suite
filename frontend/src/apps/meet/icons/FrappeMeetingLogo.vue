<!-- //// Neoffice — rewritten: the brand's Meet icon (NEOFFICE_APP_ICONS, served by neoffice_theme) instead of upstream's orange Frappe Meet mark, in the meeting header and the Meet sidebar. The component keeps its name, so every upstream use of it shows ours. -->
<script setup lang="ts">
// Served by neoffice_theme at run time: a bound src, so the build does not try to bundle it.
import { NEOFFICE_APP_ICONS } from '@/neoffice/appIcons'

const icon = NEOFFICE_APP_ICONS.meet
</script>

<template>
	<!-- //// Neoffice — the Meet icon of neoffice_theme, see the header of this file. -->
	<img :src="icon" alt="" aria-hidden="true" class="object-contain" draggable="false" />
</template>

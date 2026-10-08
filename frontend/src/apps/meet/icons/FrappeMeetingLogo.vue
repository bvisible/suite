<!-- //// Neoffice — rewritten: Neoffice's Meet icon (the apps_v2 set neoffice_theme serves) instead of upstream's orange Frappe Meet mark, in the meeting header and the Meet sidebar. The component keeps its name, so every upstream use of it shows ours. -->
<script setup lang="ts">
// Served by neoffice_theme at run time: a bound src, so the build does not try to bundle it.
const icon = '/assets/neoffice_theme/icons/apps_v2/meet.svg'
</script>

<template>
	<!-- //// Neoffice — the Meet icon of neoffice_theme, see the header of this file. -->
	<img :src="icon" alt="" aria-hidden="true" class="object-contain" draggable="false" />
</template>

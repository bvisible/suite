<!-- //// Neoffice — added file (no upstream equivalent): the host confirms the end of the notes, which ends them
     for everybody and cannot be taken back. -->
<template>
	<Dialog v-model:open="open" :title="__('End the notes?')" size="sm" :actions="actions">
		<p class="text-p-base text-ink-gray-7">
			{{ __("The notes end for everybody. The minutes will be written from what was said, and they will arrive in a few minutes.") }}
		</p>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ confirm: () => Promise<unknown> | void }>();
const open = defineModel<boolean>("open", { default: false });

const actions = computed(() => [
	{
		label: __("End the notes"),
		variant: "solid" as const,
		onClick: async ({ close }: { close: () => void }) => {
			close();
			await props.confirm();
		},
	},
	{
		label: __("Cancel"),
		variant: "subtle" as const,
		onClick: ({ close }: { close: () => void }) => close(),
	},
]);
</script>

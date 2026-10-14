<!-- //// Neoffice — added file (no upstream equivalent): what the host reads before asking the room for notes.
     It says the host is recorded too: confirming is the host's own yes. -->
<template>
	<Dialog v-model:open="open" :title="__('Take notes of this meeting?')" size="md" :actions="actions">
		<div class="space-y-3">
			<p class="text-p-base text-ink-gray-7">
				{{ __("Everybody will be asked for their agreement. Nobody is recorded without saying yes.") }}
			</p>
			<p class="text-p-base text-ink-gray-7">
				{{ __("Neoffice will write the minutes. You are recorded too, while your microphone is on.") }}
			</p>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ confirm: () => Promise<unknown> | void }>();
const open = defineModel<boolean>("open", { default: false });

const actions = computed(() => [
	{
		label: __("Ask the participants"),
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

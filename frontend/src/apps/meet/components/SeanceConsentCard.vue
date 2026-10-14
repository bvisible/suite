<!-- //// Neoffice — added file (no upstream equivalent): the card that asks each person, calmly, whether notes may
     be taken of their voice. Not a modal, not red, no sound; "I agree" and "Not for me" weigh the same. -->
<template>
	<section
		class="pointer-events-auto w-80 max-w-[calc(100vw-2rem)] rounded-6 border border-outline-gray-2 bg-surface-gray-1 p-4 shadow-lg"
		role="region"
		aria-live="polite"
		:aria-label="__('Notes of this meeting')"
		data-testid="seance-consent-card"
	>
		<div class="flex items-start gap-3">
			<span class="mt-1.5 size-2 shrink-0 rounded-full bg-[#D68A59]" aria-hidden="true" />
			<div class="min-w-0 flex-1">
				<h2 class="text-sm font-semibold text-ink-gray-9" data-testid="seance-consent-title">
					{{ title }}
				</h2>
				<p class="mt-1 text-p-sm text-ink-gray-7">
					{{ __("Neoffice will write the minutes. Your voice is recorded while your microphone is on.") }}
				</p>
				<p v-if="retention" class="mt-1 text-p-sm text-ink-gray-7" data-testid="seance-consent-retention">
					{{ retention }}
				</p>
				<p class="mt-1 text-p-sm text-ink-gray-7">
					{{ __("If other people are with you, please let them know.") }}
				</p>
			</div>
		</div>

		<div class="mt-3 flex items-center gap-2">
			<Button
				class="flex-1"
				variant="subtle"
				size="sm"
				:loading="busy"
				:label="__('I agree')"
				data-testid="seance-agree"
				@click="emit('agree')"
			/>
			<Button
				class="flex-1"
				variant="subtle"
				size="sm"
				:disabled="busy"
				:label="__('Not for me', null, 'Meet notes')"
				data-testid="seance-decline"
				@click="emit('decline')"
			/>
			<button
				type="button"
				class="flex size-7 shrink-0 items-center justify-center rounded-6 text-ink-gray-6 hover:bg-surface-gray-3"
				:aria-expanded="showMore"
				:aria-label="__('More about the notes')"
				data-testid="seance-more"
				@click="showMore = !showMore"
			>
				<span class="lucide-info size-4" aria-hidden="true" />
			</button>
		</div>

		<div v-if="showMore" class="mt-3 border-t border-outline-gray-2 pt-3" data-testid="seance-more-text">
			<p class="text-p-sm font-medium text-ink-gray-8">{{ __("Who sees the minutes?") }}</p>
			<p class="mt-1 text-p-sm text-ink-gray-7">
				{{
					__(
						"The people who agreed, and the people {0} chooses. You can take your agreement back at any time: your voice then stops being recorded, and you can ask for it to be erased.",
						[startedBy || __("the host")],
					)
				}}
			</p>
		</div>
	</section>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui";
import { computed, ref } from "vue";
import { retentionSentence } from "../utils/seancePresentation";

const props = defineProps<{
	/** Who asked for the notes (their full name). */
	startedBy?: string | null;
	/** Days the audio is kept, from the instance's setting; null while it is not known. */
	retentionDays?: number | null;
	busy?: boolean;
}>();

const emit = defineEmits<{ agree: []; decline: [] }>();

const showMore = ref(false);

const title = computed(() =>
	props.startedBy
		? __("{0} is taking notes of this meeting", [props.startedBy])
		: __("Notes are being taken of this meeting"),
);
const retention = computed(() => retentionSentence(props.retentionDays));
</script>

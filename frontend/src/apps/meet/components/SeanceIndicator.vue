<!-- //// Neoffice — added file (no upstream equivalent): the calm pill of the header while notes are being taken
     of the call, for everybody in it. A clay dot and a clock, never red: it opens what the person may do. -->
<template>
	<div ref="root" class="relative">
		<button
			ref="pill"
			type="button"
			class="flex items-center gap-2 rounded-full border border-outline-gray-2 bg-surface-gray-2 px-3 py-1 text-sm text-ink-gray-8 hover:bg-surface-gray-3"
			:aria-expanded="open"
			aria-haspopup="true"
			:aria-label="label"
			data-testid="seance-pill"
			@click="toggle"
		>
			<span class="size-2 shrink-0 rounded-full bg-[#D68A59]" aria-hidden="true" />
			<span>{{ __("Notes", null, "Meet notes") }}</span>
			<span class="tabular-nums text-ink-gray-6" data-testid="seance-clock">{{ elapsed }}</span>
		</button>

		<!-- In the body, not in the header: the header of Meet clips what falls below its own height. -->
		<Teleport to="body">
			<div
				v-if="open"
				ref="menu"
				class="fixed z-50 w-96 max-w-[calc(100vw-1rem)] rounded-6 border border-outline-gray-2 bg-surface-gray-1 p-3 shadow-lg"
				:style="{ top: `${position.top}px`, right: `${position.right}px` }"
				role="dialog"
				:aria-label="__('Notes of this meeting')"
				data-testid="seance-menu"
			>
				<p class="text-sm text-ink-gray-8" data-testid="seance-status">{{ status }}</p>

				<div class="mt-3 flex flex-col gap-2">
					<template v-if="you === 'consented'">
						<Button
							variant="subtle"
							size="sm"
							:disabled="busy"
							:label="__('Take back my agreement')"
							data-testid="seance-withdraw"
							@click="act('withdraw', false)"
						/>
						<Button
							variant="subtle"
							size="sm"
							:disabled="busy"
							:label="__('Take it back and erase what I said')"
							data-testid="seance-erase"
							@click="act('withdraw', true)"
						/>
					</template>
					<Button
						v-else-if="you === 'declined' || you === 'withdrawn'"
						variant="subtle"
						size="sm"
						:loading="busy"
						:label="__('Join the notes')"
						data-testid="seance-join"
						@click="act('agree')"
					/>
					<Button
						v-if="canEnd"
						variant="subtle"
						size="sm"
						:disabled="busy"
						:label="__('End the notes')"
						data-testid="seance-end"
						@click="act('end')"
					/>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { elapsedLabel } from "../utils/seancePresentation";

const props = defineProps<{
	startedAt?: string | null;
	you: "pending" | "consented" | "declined" | "withdrawn";
	/** The host and the co-hosts may end the notes. */
	canEnd?: boolean;
	busy?: boolean;
}>();

const emit = defineEmits<{
	agree: [];
	withdraw: [erase: boolean];
	end: [];
}>();

const open = ref(false);
const root = ref<HTMLElement | null>(null);
const pill = ref<HTMLElement | null>(null);
const menu = ref<HTMLElement | null>(null);
/** Where the menu hangs: just under the pill, its right edge on the pill's. */
const position = ref({ top: 0, right: 0 });
const now = ref(Date.now());
let timer: ReturnType<typeof setInterval> | undefined;

const elapsed = computed(() => elapsedLabel(props.startedAt, now.value));

const status = computed(() => {
	switch (props.you) {
		case "consented":
			return __("You agreed to the notes. Your voice is recorded while your microphone is on.");
		case "declined":
		case "withdrawn":
			return __("You are not being recorded.");
		default:
			return __("Notes are being taken. You have not answered yet.");
	}
});

const label = computed(() => `${__("Notes", null, "Meet notes")} ${elapsed.value}`);

function act(action: "agree" | "withdraw" | "end", erase = false) {
	open.value = false;
	if (action === "withdraw") emit("withdraw", erase);
	else if (action === "agree") emit("agree");
	else emit("end");
}

function toggle() {
	if (!open.value && pill.value) {
		const rect = pill.value.getBoundingClientRect();
		position.value = { top: Math.round(rect.bottom + 8), right: Math.max(8, Math.round(window.innerWidth - rect.right)) };
	}
	open.value = !open.value;
}

function closeOnOutsideClick(event: MouseEvent) {
	if (!open.value) return;
	const target = event.target as Node;
	if (root.value?.contains(target) || menu.value?.contains(target)) return;
	open.value = false;
}

function closeOnEscape(event: KeyboardEvent) {
	if (open.value && event.key === "Escape") open.value = false;
}

onMounted(() => {
	timer = setInterval(() => (now.value = Date.now()), 1000);
	document.addEventListener("click", closeOnOutsideClick);
	document.addEventListener("keydown", closeOnEscape);
});
onUnmounted(() => {
	if (timer) clearInterval(timer);
	document.removeEventListener("click", closeOnOutsideClick);
	document.removeEventListener("keydown", closeOnEscape);
});
</script>

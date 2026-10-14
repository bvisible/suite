//// Neoffice — added file (no upstream equivalent): the state of the notes taken of a call (a "séance"), read
//// by the header pill, the consent card, the people panel and the host's button. The call server (SFU) says
//// whether notes are running and who is captured; the instance keeps the record of each person's yes.
import { defineStore } from "pinia";
import { computed, ref } from "vue";

/** A person's answer as the call server tells it: `pending` until they say yes or no. */
export type SeanceAnswer = "pending" | "consented" | "declined" | "withdrawn";

/** What the instance says a signed-in person may do with the notes of this call. */
export interface SeanceCapabilities {
	enabled: boolean;
	can_start: boolean;
	reason: string | null;
	meeting: string | null;
	owner: string | null;
}

interface SeanceBeginning {
	seanceId: string;
	startedAt: string | null;
	startedBy: { id: string; name: string } | null;
	capturing: string[];
}

export const useSeanceStore = defineStore("meet-seance", () => {
	const active = ref(false);
	const seanceId = ref<string | null>(null);
	const startedAt = ref<string | null>(null);
	const startedBy = ref<{ id: string; name: string } | null>(null);
	const capturing = ref<string[]>([]);
	const you = ref<SeanceAnswer>("pending");
	/** Days the audio is kept, read from the instance's setting; null until the instance said. */
	const retentionDays = ref<number | null>(null);
	const capabilities = ref<SeanceCapabilities | null>(null);
	const busy = ref(false);

	/** The séance of this call is running: remember who started it and who is captured. */
	function begin(next: SeanceBeginning) {
		if (seanceId.value !== next.seanceId) {
			// Another séance than the one we knew: what we knew of our answer does not carry over.
			you.value = "pending";
			retentionDays.value = null;
		}
		active.value = true;
		seanceId.value = next.seanceId;
		startedAt.value = next.startedAt;
		startedBy.value = next.startedBy;
		capturing.value = next.capturing;
	}

	/** The séance is over (or there is none): nothing of it stays on screen. */
	function end() {
		active.value = false;
		seanceId.value = null;
		startedAt.value = null;
		startedBy.value = null;
		capturing.value = [];
		you.value = "pending";
	}

	function isCaptured(userId: string | null | undefined): boolean {
		return Boolean(active.value && userId && capturing.value.includes(userId));
	}

	/** True while a person has been asked and has not answered: the card is on screen. */
	const isAsked = computed(() => active.value && you.value === "pending");

	function $reset() {
		end();
		retentionDays.value = null;
		capabilities.value = null;
		busy.value = false;
	}

	return {
		active,
		seanceId,
		startedAt,
		startedBy,
		capturing,
		you,
		retentionDays,
		capabilities,
		busy,
		isAsked,
		isCaptured,
		begin,
		end,
		$reset,
	};
});

export type SeanceStore = ReturnType<typeof useSeanceStore>;

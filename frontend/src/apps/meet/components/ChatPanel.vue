<template>
	<Transition
		enter-active-class="transition-all duration-300 ease-out"
		enter-from-class="opacity-0 transform translate-x-full"
		enter-to-class="opacity-100 transform translate-x-0"
		leave-active-class="transition-all duration-300 ease-in"
		leave-from-class="opacity-100 transform translate-x-0"
		leave-to-class="opacity-0 transform translate-x-full"
	>
		<div v-show="open" class="h-full py-4 flex justify-end">
			<div
				class="w-80 sm:w-96 bg-white border border-gray-200 shadow-xl flex flex-col z-40 h-full rounded-lg mr-4"
			>
				<div class="flex items-center justify-between p-4 border-b border-gray-200">
					<div class="text-gray-900 font-medium">Chat</div>
					<lucide-x
						@click="$emit('close')"
						class="w-4 h-4 text-gray-900 cursor-pointer hover:text-gray-600"
					/>
				</div>

				<div ref="listEl" class="flex-1 overflow-y-auto p-4 space-y-4">
					<div v-for="group in groupedMessages" :key="group.id" class="min-w-0">
						<div class="text-xs flex items-center gap-2">
							<span class="truncate font-medium">{{ group.user_name }}</span>
							<span class="text-gray-600">•</span>
							<span class="text-gray-600">{{ time(group.timestamp) }}</span>
						</div>
						<div class="mt-1 space-y-2">
							<div
								v-for="message in group.messages"
								:key="message.id"
								class="text-sm text-gray-900 whitespace-pre-wrap break-words"
							>
								{{ message.message }}
							</div>
						</div>
					</div>
					<div v-if="messages.length === 0" class="text-gray-500 text-sm text-center mt-8">
						No messages yet
					</div>
				</div>

				<form class="p-2" @submit.prevent="handleSend">
					<div class="flex gap-2 py-2">
						<FormControl
							size="md"
							v-model="draft"
							@keydown.enter.exact.prevent="handleSend"
							placeholder="Type a message"
							class="flex-1"
							autocomplete="off"
						/>
						<Button size="md" type="submit" variant="outline"> Send </Button>
					</div>
				</form>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import { Button, FormControl } from "frappe-ui";
import { computed, nextTick, ref, toRefs, watch } from "vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	userId: { type: String, default: "" },
	userName: { type: String, default: "" },
	messages: { type: [Array, Object], default: () => [] },
});

const emit = defineEmits(["close", "send"]);
const listEl = ref(null);
const { messages } = toRefs(props);
const draft = ref("");

const groupedMessages = computed(() => {
	if (!messages.value || messages.value.length === 0) return [];

	const groups = [];
	let currentGroup = null;

	for (const message of messages.value) {
		if (!currentGroup || currentGroup.user_name !== message.user_name) {
			currentGroup = {
				id: message.id,
				user_name: message.user_name,
				timestamp: message.timestamp,
				messages: [message],
			};
			groups.push(currentGroup);
		} else {
			currentGroup.messages.push(message);
		}
	}

	return groups;
});

function time(ts) {
	try {
		return new Date(ts).toLocaleTimeString([], {
			hour: "2-digit",
			minute: "2-digit",
			hour12: true,
		});
	} catch {
		return "";
	}
}

function handleSend() {
	const text = draft.value.trim();
	if (!text) return;
	emit("send", text);
	draft.value = "";
}

watch(
	messages,
	async () => {
		await nextTick();
		try {
			const el = listEl.value;
			el.scrollTop = el.scrollHeight;
		} catch {}
	},
	{ deep: true },
);
</script>

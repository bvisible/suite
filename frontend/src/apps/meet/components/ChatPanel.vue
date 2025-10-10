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
							<span class="text-gray-600">{{ time(group.timestamp) }}</span>
						</div>
						<div class="my-1 space-y-2">
							<div
								v-for="message in group.messages"
								:key="message.id"
								class="text-sm text-gray-900 whitespace-pre-wrap break-words"
							>
								<span v-html="linkify(message.message)"></span>
							</div>
						</div>
					</div>
					<div v-if="messages.length === 0" class="text-gray-500 text-sm text-center mt-8">
						No messages yet
					</div>
				</div>

				<form class="p-2 relative" @submit.prevent="handleSend">
					<div class="flex gap-2 py-2">
						<FormControl
							size="md"
							v-model="draft"
							@input="handleInput"
							@keydown="handleKeydown"
							placeholder="Type a message"
							class="flex-1"
							autocomplete="off"
						/>
						<Button size="md" type="submit" variant="outline"> Send </Button>
					</div>
					<EmojiPicker
						:show="showEmojiPicker"
						:filtered-emojis="filteredEmojis"
						:selected-index="selectedEmojiIndex"
						@select="addEmoji"
					/>
				</form>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import data from "@emoji-mart/data";
import { SearchIndex, init } from "emoji-mart";
import { Button, FormControl } from "frappe-ui";
import { computed, nextTick, onMounted, ref, toRefs, watch } from "vue";
import EmojiPicker from "./EmojiPicker.vue";

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
const showEmojiPicker = ref(false);
const selectedEmojiIndex = ref(0);
const filteredEmojis = ref([]);
const isEmojiDataReady = ref(false);

onMounted(async () => {
	try {
		await init({ data });
		isEmojiDataReady.value = true;
	} catch (error) {
		console.error("Failed to initialize emoji data:", error);
	}
});

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

function linkify(text) {
	const urlRegex = /(https?:\/\/[^\s]+)/g;
	return text.replace(
		urlRegex,
		'<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-500 underline">$1</a>',
	);
}

const emojiQuery = computed(() => {
	const colonIndex = draft.value.lastIndexOf(":");
	if (colonIndex === -1) return "";
	const afterColon = draft.value.slice(colonIndex + 1);
	if (afterColon.includes(" ")) return "";
	// don't allow special characters in emoji query
	// or while pasting url you'll have emoji picker popup
	if (!/^[a-zA-Z0-9]*$/.test(afterColon)) return "";
	return afterColon;
});

watch(emojiQuery, async (query) => {
	if (!isEmojiDataReady.value || !query) {
		filteredEmojis.value = [];
		return;
	}
	try {
		const results = await SearchIndex.search(query, { maxResults: 10 });
		filteredEmojis.value = results.map((emoji) => ({
			emoji: emoji.skins[0].native,
			keywords: emoji.keywords || [],
		}));
		if (selectedEmojiIndex.value >= filteredEmojis.value.length) {
			selectedEmojiIndex.value = 0;
		}
	} catch (error) {
		filteredEmojis.value = [];
	}
});

function handleInput() {
	const wasShown = showEmojiPicker.value;
	showEmojiPicker.value = emojiQuery.value.length > 0;
	if (showEmojiPicker.value && !wasShown) {
		selectedEmojiIndex.value = 0;
	}
}

function handleKeydown(event) {
	if (!showEmojiPicker.value) return;
	const { key } = event;
	if (key === "ArrowDown") {
		event.preventDefault();
		selectedEmojiIndex.value =
			(selectedEmojiIndex.value + 1) % filteredEmojis.value.length;
	} else if (key === "ArrowUp") {
		event.preventDefault();
		selectedEmojiIndex.value =
			selectedEmojiIndex.value === 0
				? filteredEmojis.value.length - 1
				: selectedEmojiIndex.value - 1;
	} else if (key === "Enter") {
		event.preventDefault();
		if (filteredEmojis.value.length > 0) {
			addEmoji(filteredEmojis.value[selectedEmojiIndex.value].emoji);
		}
	} else if (key === "Escape") {
		event.preventDefault();
		showEmojiPicker.value = false;
	}
}

function addEmoji(emoji) {
	const colonIndex = draft.value.lastIndexOf(":");
	const beforeColon = draft.value.slice(0, colonIndex);
	draft.value = beforeColon + emoji;
	showEmojiPicker.value = false;
}

function handleSend() {
	if (showEmojiPicker.value && filteredEmojis.value.length > 0) {
		addEmoji(filteredEmojis.value[selectedEmojiIndex.value].emoji);
		return;
	}
	const text = draft.value.trim();
	if (!text) return;
	emit("send", text);
	draft.value = "";
	showEmojiPicker.value = false;
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

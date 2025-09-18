<template>
	<div class="flex-1 flex flex-col">
		<div class="bg-gray-50 px-6 py-4 flex-shrink-0">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2 cursor-pointer" @click="$router.push('/')">
					<FrappeMeetingLogo class="h-8" />
					<h4 class="text-gray-900 text-base">Frappe Meet</h4>
				</div>
			</div>
		</div>

		<div class="flex-1 flex md:flex-row flex-col p-8 bg-gray-50 text-gray-900 gap-6">
			<div
				class="w-full md:flex-[3] flex flex-col justify-center space-y-8 max-w-4xl mx-auto md:mx-0"
			>
				<div
					class="relative bg-black rounded-lg overflow-hidden aspect-video max-h-[480px]"
				>
					<video
						:ref="(el) => setLocalVideoRef && setLocalVideoRef(el)"
						class="w-full h-full object-cover transform scale-x-[-1]"
						autoplay
						muted
						playsinline
					/>

					<div
						v-if="!isCameraOn"
						class="absolute inset-0 bg-gray-700 flex items-center justify-center"
					>
						<div class="text-center text-white">
							<MeetingAvatar
								:label="userInitials"
								:image="userAvatar"
								:tiles="1"
								class="mx-auto mb-4"
							/>
							<p class="text-xl font-medium">{{ currentUserName }}</p>
						</div>
					</div>
				</div>

				<!-- Controls -->
				<div class="flex items-center space-x-6 justify-center">
					<Button
						@click="$emit('toggle-microphone')"
						:variant="isMicOn ? 'solid' : 'solid'"
						:theme="isMicOn ? 'gray' : 'red'"
						size="lg"
						class="w-12 h-12 rounded-full p-0"
						:title="'Toggle Audio (' + ($platform === 'mac' ? '⌘+D' : 'Ctrl+D') + ')'"
					>
						<template #icon>
							<lucide-mic-off v-if="!isMicOn" class="w-6 h-6 text-white" />
							<lucide-mic v-else class="w-6 h-6 text-white" />
						</template>
					</Button>

					<Button
						@click="$emit('toggle-camera')"
						:variant="isCameraOn ? 'solid' : 'solid'"
						:theme="isCameraOn ? 'gray' : 'red'"
						size="lg"
						class="w-12 h-12 rounded-full p-0"
						:title="'Toggle Video (' + ($platform === 'mac' ? '⌘+E' : 'Ctrl+E') + ')'"
					>
						<template #icon>
							<lucide-video-off v-if="!isCameraOn" class="w-6 h-6 text-white" />
							<lucide-video v-else class="w-6 h-6 text-white" />
						</template>
					</Button>
				</div>
			</div>

			<div class="w-full md:flex-[1] flex items-center justify-center">
				<div
					class="w-full h-full flex flex-col items-center justify-center md:justify-center space-y-8"
				>
					<div class="text-center text-gray-700">
						<div class="text-xl font-medium">Ready to join {{ meetingTitle }}?</div>
					</div>
					<div>
						<Button
							@click="$emit('join-from-preview')"
							variant="solid"
							size="lg"
							:loading="isConnecting"
						>
							Join Meeting
						</Button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, defineEmits, defineProps } from "vue";
import MeetingAvatar from "../components/MeetingAvatar.vue";
import FrappeMeetingLogo from "../icons/FrappeMeetingLogo.vue";

const props = defineProps({
	isCameraOn: Boolean,
	isMicOn: Boolean,
	currentUser: Object,
	userInitials: String,
	userAvatar: String,
	isConnecting: Boolean,
	meetingTitle: { type: String, default: "" },
	setLocalVideoRef: Function,
});

const emit = defineEmits([
	"toggle-microphone",
	"toggle-camera",
	"join-from-preview",
]);

const currentUserName = computed(
	() => props.currentUser?.full_name || props.currentUser?.name || "You",
);
</script>

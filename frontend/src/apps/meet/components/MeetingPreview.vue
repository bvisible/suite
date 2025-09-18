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

		<div class="flex-1 flex lg:flex-row flex-col bg-gray-50 text-gray-900">
			<div class="max-w-7xl mx-auto w-full flex lg:flex-row flex-col px-6 lg:px-8">
				<!-- Video Section -->
				<div class="lg:flex-[2] flex flex-col justify-center p-6 lg:pr-4">
					<div class="max-w-3xl mx-auto w-full">
						<div
							class="relative bg-black rounded-xl overflow-hidden aspect-video shadow-xl"
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
								class="absolute inset-0 bg-gray-800 flex items-center justify-center"
							>
								<div class="text-center text-white">
									<MeetingAvatar
										:label="userInitials"
										:image="userAvatar"
										:tiles="1"
										class="mx-auto mb-4 w-20 h-20"
									/>
									<p class="text-xl font-medium">{{ currentUserName }}</p>
								</div>
							</div>
						</div>

						<!-- Controls -->
						<div class="flex items-center justify-center space-x-4 mt-6">
							<Button
								@click="$emit('toggle-microphone')"
								:variant="isMicOn ? 'solid' : 'solid'"
								:theme="isMicOn ? 'gray' : 'red'"
								size="lg"
								:title="
									'Toggle Audio (' +
									($platform === 'mac' ? '⌘+D' : 'Ctrl+D') +
									')'
								"
							>
								<template #icon>
									<lucide-mic-off v-if="!isMicOn" class="w-5 h-5" />
									<lucide-mic v-else class="w-5 h-5" />
								</template>
							</Button>

							<Button
								@click="$emit('toggle-camera')"
								:variant="isCameraOn ? 'solid' : 'solid'"
								:theme="isCameraOn ? 'gray' : 'red'"
								size="lg"
								:title="
									'Toggle Video (' +
									($platform === 'mac' ? '⌘+E' : 'Ctrl+E') +
									')'
								"
							>
								<template #icon>
									<lucide-video-off v-if="!isCameraOn" class="w-5 h-5" />
									<lucide-video v-else class="w-5 h-5" />
								</template>
							</Button>
						</div>
					</div>
				</div>

				<!-- Join Section -->
				<div class="lg:flex-[1] flex items-center justify-center p-6 lg:pl-4">
					<div class="text-center max-w-sm">
						<div>
							<h2 class="text-2xl font-semibold text-gray-900 mb-2">
								Ready to join?
							</h2>
							<p class="text-lg text-gray-600 mb-8">{{ meetingTitle }}</p>
						</div>

						<div v-if="!isNaN(participantsCount)" class="text-sm text-gray-500 mb-4">
							<span v-if="participantsCount > 0">
								{{ getParticipantText(participantsCount) }}
							</span>
							<span v-else>No one in this call</span>
						</div>

						<div>
							<Button
								@click="$emit('join-from-preview')"
								variant="solid"
								:loading="isConnecting"
								class="px-10 py-6 text-lg"
							>
								Join Meeting
							</Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { frappeRequest } from "frappe-ui";
import {
	computed,
	defineEmits,
	defineProps,
	onMounted,
	onUnmounted,
	ref,
} from "vue";
import MeetingAvatar from "../components/MeetingAvatar.vue";
import { session } from "../data/session.js";
import FrappeMeetingLogo from "../icons/FrappeMeetingLogo.vue";

const props = defineProps({
	isCameraOn: Boolean,
	isMicOn: Boolean,
	currentUser: Object,
	userInitials: String,
	userAvatar: String,
	isConnecting: Boolean,
	meetingTitle: { type: String, default: "" },
	meetingId: { type: String, required: true },
	setLocalVideoRef: Function,
});

const emit = defineEmits([
	"toggle-microphone",
	"toggle-camera",
	"join-from-preview",
]);

const participantsCount = ref(0);
let pollInterval = null;

const fetchParticipants = async () => {
	try {
		if (!session.isLoggedIn) return;

		const result = await frappeRequest({
			url: "sae.api.meeting.get_sfu_connection_details",
			params: { meeting_id: props.meetingId },
		});

		if (!result?.success) {
			throw new Error(result?.error || "Failed to get SFU details");
		}

		const sfuUrl = `${result.sfu_url}${result.sfu_url.startsWith("http://") ? `:${result.sfu_port}` : ""}`;

		const roomsResponse = await fetch(`${sfuUrl}/rooms`);
		const roomsData = await roomsResponse.json();

		const ourRoom = roomsData.rooms.find((room) => room.id === props.meetingId);
		participantsCount.value = ourRoom ? ourRoom.peerCount : 0;
	} catch (err) {
		console.warn("Could not fetch participants count:", err?.message || err);
	}
};

onMounted(() => {
	fetchParticipants();
	pollInterval = setInterval(fetchParticipants, 10000);
});

onUnmounted(() => {
	if (pollInterval) {
		clearInterval(pollInterval);
		pollInterval = null;
	}
});

const currentUserName = computed(
	() => props.currentUser?.full_name || props.currentUser?.name || "You",
);

const getParticipantText = (count) => {
	if (count === 1) {
		return "1 user in the call";
	}
	return `${count} users in the call`;
};
</script>

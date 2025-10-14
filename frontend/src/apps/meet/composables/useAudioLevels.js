import { onMounted, onUnmounted, ref } from "vue";
import { getSFUMeetingManager } from "../utils/sfu-meeting-manager.js";
import { useMeetingState } from "./useMeetingState.js";

/**
 * Composable to get audio stream for a participant
 * Returns the MediaStream containing the audio track
 */
export function useAudioStream(participantId) {
	const stream = ref(null);
	const meetingState = useMeetingState();

	const getStream = () => {
		try {
			if (participantId === meetingState.currentUser.value?.user_id) {
				// Local user
				const audioTrack = meetingState.localStream.value?.getAudioTracks()[0];
				if (audioTrack) {
					stream.value = new MediaStream([audioTrack]);
				}
			} else {
				// Remote user - try to get from consumer manager first
				const sfuManager = getSFUMeetingManager();
				if (sfuManager?.consumerManager) {
					const audioConsumer =
						sfuManager.consumerManager.getAudioConsumer(participantId);
					if (audioConsumer?.track) {
						stream.value = new MediaStream([audioConsumer.track]);
						return;
					}
				}

				// Fallback to audio element
				if (sfuManager?.videoManager) {
					const audioElement =
						sfuManager.videoManager.audioElements.get(participantId);
					if (audioElement?.srcObject) {
						stream.value = audioElement.srcObject;
					}
				}
			}
		} catch (error) {
			console.error("Error getting audio stream:", error);
		}
	};

	onMounted(() => {
		getStream();
		// Re-check periodically in case stream becomes available later
		const interval = setInterval(getStream, 1000);
		onUnmounted(() => clearInterval(interval));
	});

	return { stream };
}

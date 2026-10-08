import { useKeyboardShortcut } from "frappe-ui";
import { reactive } from "vue";
import { pushToTalkEnabled } from "../data/mediaPreferences";

export const meetingControls = reactive({
	toggleMicrophone: async () => {},
	toggleCamera: async () => {},
	isMicOn: false,
});

export function useKeyboardShortcuts(isActive?: () => boolean) {
	const isActiveFn = isActive || (() => true);

	let unmutedByPushToTalk = false;

	useKeyboardShortcut([
		{
			combo: "Mod+D",
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			description: __("Toggle microphone"),
			group: __("Meeting controls"),
			enabled: isNotTyping,
			handler: () => {
				if (isActiveFn()) meetingControls.toggleMicrophone();
			},
		},
		{
			combo: "Mod+E",
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			description: __("Toggle camera"),
			group: __("Meeting controls"),
			enabled: isNotTyping,
			handler: () => {
				if (isActiveFn()) meetingControls.toggleCamera();
			},
		},
		{
			combo: "Space",
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			description: __("Push to talk"),
			group: __("Meeting controls"),
			enabled: isNotTyping,
			onHold: () => {
				if (isActiveFn() && pushToTalkEnabled.value && !meetingControls.isMicOn) {
					unmutedByPushToTalk = true;
					meetingControls.toggleMicrophone();
				}
			},
			onRelease: () => {
				if (unmutedByPushToTalk) {
					unmutedByPushToTalk = false;
					if (meetingControls.isMicOn) {
						meetingControls.toggleMicrophone();
					}
				}
			},
		},
	]);
}

function isNotTyping() {
	return !document.activeElement?.closest(
		'input, textarea, [contenteditable="true"], [contenteditable=""]',
	);
}

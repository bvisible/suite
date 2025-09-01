import { ref } from "vue";

function readBool(key, def = true) {
	const v = localStorage.getItem(key);
	if (v === null) return def;
	return v === "1";
}

export const micEnabled = ref(readBool("mediaPref.mic", true));
export const cameraEnabled = ref(readBool("mediaPref.camera", true));

export function setMicEnabled(val) {
	micEnabled.value = !!val;
	try {
		localStorage.setItem("mediaPref.mic", micEnabled.value ? "1" : "0");
	} catch (_) {}
}

export function setCameraEnabled(val) {
	cameraEnabled.value = !!val;
	try {
		localStorage.setItem("mediaPref.camera", cameraEnabled.value ? "1" : "0");
	} catch (_) {}
}

export function loadMediaPreferences() {
	micEnabled.value = readBool("mediaPref.mic", true);
	cameraEnabled.value = readBool("mediaPref.camera", true);
}

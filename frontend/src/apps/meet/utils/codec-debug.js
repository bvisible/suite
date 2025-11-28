/**
 * Debug Utility for Codec Information
 * Displays current codec strategy and capabilities
 */

import { detectVideoCapabilities } from "./media/codec-capabilities.js";

export function logCodecInfo() {
	const caps = detectVideoCapabilities();

	console.group("🎥 Video Codec Information");
	console.log("Strategy:", caps.preferredStrategy.toUpperCase());
	console.log("VP8 Support:", caps.supportsVP8 ? "✅" : "❌");
	console.log("VP9 Support:", caps.supportsVP9 ? "✅" : "❌");
	console.log("VP9 SVC Support:", caps.supportsVP9SVC ? "✅" : "❌");

	if (caps.supportsVP9SVC) {
		console.log("Available Scalability Modes:", caps.availableScalabilityModes);
	}

	console.groupEnd();

	return caps;
}

export function getCodecDebugInfo() {
	const caps = detectVideoCapabilities();

	return {
		strategy: caps.preferredStrategy,
		browser: getBrowserInfo(),
		codecs: {
			vp8: caps.supportsVP8,
			vp9: caps.supportsVP9,
			vp9SVC: caps.supportsVP9SVC,
		},
		scalabilityModes: caps.availableScalabilityModes,
	};
}

function getBrowserInfo() {
	const ua = navigator.userAgent;
	let browser = "Unknown";
	let version = "";

	if (ua.includes("Chrome") && !ua.includes("Edg")) {
		browser = "Chrome";
		version = ua.match(/Chrome\/(\d+)/)?.[1] || "";
	} else if (ua.includes("Edg")) {
		browser = "Edge";
		version = ua.match(/Edg\/(\d+)/)?.[1] || "";
	} else if (ua.includes("Firefox")) {
		browser = "Firefox";
		version = ua.match(/Firefox\/(\d+)/)?.[1] || "";
	} else if (ua.includes("Safari") && !ua.includes("Chrome")) {
		browser = "Safari";
		version = ua.match(/Version\/(\d+)/)?.[1] || "";
	}

	return { name: browser, version };
}

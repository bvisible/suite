/**
 * Codec Capabilities Detection
 * Detects browser support for VP9 SVC and other advanced video features
 *
 * VP9 SVC is ENABLED using L1T3 mode (conservative, compatible):
 * - Chrome/Edge: VP9 SVC with L1T3 (1 spatial, 3 temporal layers)
 * - Other browsers: VP8 simulcast (3 independent streams)
 *
 * Note: L3T3_KEY causes "encoding.spatialLayers does not match consumableRtpEncodings"
 * error in mediasoup, so we use L1T3 for maximum compatibility
 */ let cachedCapabilities = null;

/**
 * Detect if browser is Chrome/Chromium-based (likely supports VP9 SVC)
 */
function isChromiumBased() {
	const ua = navigator.userAgent;
	// Chrome, Edge, Opera, Brave, etc.
	return (
		(ua.includes("Chrome") || ua.includes("Chromium")) &&
		!ua.includes("Edg") && // Exclude old Edge
		!ua.includes("OPR") // Opera can be unreliable
	);
}

/**
 * Detect video codec capabilities
 * @returns {Object} Capability information
 */
export function detectVideoCapabilities() {
	// Return cached result if available
	if (cachedCapabilities) {
		return cachedCapabilities;
	}

	const capabilities = {
		supportsVP9: false,
		supportsVP9SVC: false,
		supportsVP8: false,
		availableScalabilityModes: [],
		preferredStrategy: "simulcast", // default to simulcast
		browser: "",
	};

	try {
		// Check if RTCRtpSender.getCapabilities is available
		if (!RTCRtpSender?.getCapabilities) {
			console.warn(
				"⚠️ RTCRtpSender.getCapabilities not available, falling back to VP8 simulcast",
			);
			capabilities.supportsVP8 = true;
			cachedCapabilities = capabilities;
			return capabilities;
		}

		const caps = RTCRtpSender.getCapabilities("video");

		if (!caps?.codecs) {
			console.warn(
				"⚠️ No video codecs available, falling back to VP8 simulcast",
			);
			capabilities.supportsVP8 = true;
			cachedCapabilities = capabilities;
			return capabilities;
		}

		// Check for VP8 support
		const vp8Codec = caps.codecs.find((codec) =>
			codec.mimeType.toLowerCase().includes("vp8"),
		);
		capabilities.supportsVP8 = !!vp8Codec;

		// Check for VP9 support
		const vp9Codec = caps.codecs.find((codec) =>
			codec.mimeType.toLowerCase().includes("vp9"),
		);
		capabilities.supportsVP9 = !!vp9Codec;

		// Detect browser
		const ua = navigator.userAgent;
		if (ua.includes("Chrome")) capabilities.browser = "Chrome";
		else if (ua.includes("Firefox")) capabilities.browser = "Firefox";
		else if (ua.includes("Safari") && !ua.includes("Chrome"))
			capabilities.browser = "Safari";
		else if (ua.includes("Edg")) capabilities.browser = "Edge";

		// VP9 SVC support detection:
		// Note: RTCRtpSender.getCapabilities() doesn't expose scalabilityModes reliably
		// We use browser detection as a heuristic instead

		// DISABLED: VP9 SVC due to cross-browser compatibility issues
		// Firefox and Safari have poor VP9 support, can't decode VP9 streams from Chrome
		// Keeping VP8 simulcast for universal compatibility across all browsers
		const ENABLE_VP9_SVC = false;

		if (ENABLE_VP9_SVC && capabilities.supportsVP9 && isChromiumBased()) {
			// Chrome/Chromium supports VP9 SVC since v94
			// Using L3T3_KEY: 3 spatial layers (resolutions), 3 temporal layers (framerate)
			// Spatial layers provide quality adaptation, temporal layers stay at max for best FPS
			capabilities.supportsVP9SVC = true;
			capabilities.availableScalabilityModes = ["L3T3_KEY"];
			capabilities.preferredStrategy = "svc";

			console.log(
				"✅ VP9 SVC enabled (Chromium-based browser with VP9 support)",
			);
		}

		// Log detected capabilities
		console.log("🎥 Video codec capabilities detected:", {
			Browser: capabilities.browser,
			VP8: capabilities.supportsVP8,
			VP9: capabilities.supportsVP9,
			"VP9-SVC": capabilities.supportsVP9SVC,
			scalabilityModes: capabilities.availableScalabilityModes,
			preferredStrategy: capabilities.preferredStrategy,
		});
	} catch (error) {
		console.error("❌ Error detecting video capabilities:", error);
		capabilities.supportsVP8 = true; // Safe fallback
	}

	cachedCapabilities = capabilities;
	return capabilities;
}

/**
 * Check if the browser supports VP9 SVC
 * @returns {boolean}
 */
export function supportsVP9SVC() {
	const caps = detectVideoCapabilities();
	return caps.supportsVP9SVC;
}

/**
 * Check if the browser supports VP8
 * @returns {boolean}
 */
export function supportsVP8() {
	const caps = detectVideoCapabilities();
	return caps.supportsVP8;
}

/**
 * Get the preferred encoding strategy
 * @returns {'svc' | 'simulcast'}
 */
export function getPreferredStrategy() {
	const caps = detectVideoCapabilities();
	return caps.preferredStrategy;
}

/**
 * Get the best scalability mode for SVC
 * Using conservative L1T3 mode for better compatibility
 * @param {string} sourceType - 'webcam' or 'screen' (affects mode selection)
 * @returns {string | null}
 */
export function getBestScalabilityMode(sourceType = "webcam") {
	const caps = detectVideoCapabilities();

	if (!caps.supportsVP9SVC) {
		return null;
	}

	const modes = caps.availableScalabilityModes;

	// Using L1T3 (1 spatial, 3 temporal) for all sources
	// This is the most compatible mode and avoids consumer creation errors
	const preferredModes = ["L1T3"];

	// Find the first preferred mode that's available
	for (const mode of preferredModes) {
		if (modes.includes(mode)) {
			return mode;
		}
	}

	// Return the first available mode as fallback
	return modes[0] || null;
}

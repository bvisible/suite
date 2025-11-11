// layers for simulcast video streaming (adaptive streaming)
// layer 0: low quality (200 kbps)
// layer 1: medium quality (400 kbps)
// layer 2: high quality (1000 kbps)
export const videoEncodings = [
	{ maxBitrate: 200000 },
	{ maxBitrate: 400000 },
	{ maxBitrate: 1000000 },
];

// layer 0: medium quality (800 kbps)
// layer 1: high quality (1.5 Mbps
export const screenEncodings = [
	{ maxBitrate: 800000 },
	{ maxBitrate: 1500000 },
];

export const videoCodecOptions = {
	videoGoogleStartBitrate: 2000,
};

export default {
	videoEncodings,
	screenEncodings,
	videoCodecOptions,
};

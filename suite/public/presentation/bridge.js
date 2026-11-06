// //// Neoffice — added file (no upstream equivalent): placed in the entry file of a shared presentation, inside its
// //// sandboxed frame (suite/drive/presentation/renderer.py). It tells the visitor's page which slide is on screen, how
// //// far each video went and when the person touches the slides; it turns the page's arrows into the presentation's.
// //// It reads a reveal.js deck (its API), and any deck that marks its slide `.current` or writes its number in the hash.
(function () {
	"use strict";
	if (window.parent === window) return;
	const post = (message) => window.parent.postMessage(Object.assign({ source: "np-bridge" }, message), "*");

	function slides() {
		const reveal = document.querySelectorAll(".reveal .slides > section");
		if (reveal.length) return reveal;
		return document.querySelectorAll(".slide, section.slide");
	}
	function position() {
		if (window.Reveal && typeof window.Reveal.getIndices === "function" && window.Reveal.isReady && window.Reveal.isReady()) {
			return { index: window.Reveal.getIndices().h + 1, total: window.Reveal.getTotalSlides() };
		}
		const all = Array.from(slides());
		const shown = all.findIndex((el) => el.classList.contains("current") || el.classList.contains("present"));
		if (shown >= 0) return { index: shown + 1, total: all.length };
		const hash = (location.hash || "").replace(/^#\/?/, "");
		const n = parseInt(hash.split("/")[0], 10);
		const fromReveal = (location.hash || "").startsWith("#/");
		return { index: Number.isFinite(n) ? n + (fromReveal ? 1 : 0) : 1, total: all.length };
	}

	let last = "";
	function report() {
		const at = position();
		const key = at.index + "/" + at.total;
		if (key !== last) {
			last = key;
			post({ type: "slide", index: at.index, total: at.total });
		}
	}
	window.addEventListener("hashchange", report);
	setInterval(report, 500);

	// How far each video went: the share of it really played, not where the cursor was dragged.
	const watched = new WeakMap();
	function percent(video) {
		if (!video.duration || !isFinite(video.duration)) return 0;
		let played = 0;
		for (let i = 0; i < video.played.length; i++) played += video.played.end(i) - video.played.start(i);
		return Math.min(100, Math.round((played / video.duration) * 100));
	}
	function follow(video) {
		if (watched.has(video)) return;
		watched.set(video, 0);
		const src = () => (video.currentSrc || video.src || "").split("/c/").pop().replace(/^[^/]+\//, "") || "video";
		const send = (playing) => post({ type: "video", src: src(), percent: video.ended ? 100 : percent(video), playing });
		let lastSent = 0;
		video.addEventListener("play", () => send(true));
		video.addEventListener("pause", () => send(false));
		video.addEventListener("ended", () => send(false));
		video.addEventListener("timeupdate", () => {
			if (Date.now() - lastSent > 2000) { lastSent = Date.now(); send(!video.paused); }
		});
	}
	const scan = () => document.querySelectorAll("video").forEach(follow);
	scan();
	new MutationObserver(scan).observe(document.documentElement, { childList: true, subtree: true });

	let lastActivity = 0;
	["pointermove", "keydown", "touchstart", "wheel", "click"].forEach((name) =>
		window.addEventListener(name, () => {
			if (Date.now() - lastActivity > 5000) { lastActivity = Date.now(); post({ type: "activity" }); }
		}, { passive: true })
	);

	window.addEventListener("message", (event) => {
		if (event.source !== window.parent) return;
		const data = event.data || {};
		if (data.source !== "np-viewer" || data.type !== "go") return;
		if (window.Reveal && typeof window.Reveal.next === "function") {
			data.dir > 0 ? window.Reveal.next() : window.Reveal.prev();
		} else {
			const key = data.dir > 0 ? "ArrowRight" : "ArrowLeft";
			document.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
		}
	});
})();

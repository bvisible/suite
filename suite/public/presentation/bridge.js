// //// Neoffice — added file (no upstream equivalent): placed in the entry file of a shared presentation, inside its
// //// sandboxed frame (suite/drive/presentation/renderer.py). It tells the visitor's page which slide is on screen, how
// //// far each video went and when the person touches the slides; it turns the page's arrows into the presentation's.
// //// It reads a reveal.js deck (its API), and any deck that marks its slide `.current` or writes its number in the hash.
// //// A video with sound starts silent, as soon as it is on screen, with a big button to turn its sound on (Jérémy,
// //// 09.11: « il faut surtout les mettre en mute »); a video the deck marks `muted` (a loop that shows a gesture) has
// //// no sound to offer and gets no button.
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
	// Sound --------------------------------------------------------------------------------------------------------------
	const ICON = (paths) =>
		'<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4V5z"/>' + paths + "</svg>";
	const SOUND_OFF = ICON('<path d="m22 9-6 6M16 9l6 6"/>');
	const SOUND_ON = ICON('<path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>');
	let words = { soundOn: "Turn the sound on", soundOff: "Turn the sound off" };
	const voiced = new WeakSet(); // the videos whose sound the person turned on
	const redraws = [];
	function soundStyle() {
		if (document.getElementById("np-sound-style")) return;
		const style = document.createElement("style");
		style.id = "np-sound-style";
		style.textContent = [
			".np-sound{all:unset;box-sizing:border-box;position:absolute;right:20px;bottom:20px;z-index:5;display:flex;align-items:center;gap:10px;",
			"height:84px;min-width:84px;padding:0 28px 0 22px;border-radius:999px;background:rgba(20,20,20,.78);color:#fffdf8;cursor:pointer;",
			"font:700 19px/1 Karla,system-ui,sans-serif;box-shadow:0 12px 30px -10px rgba(0,0,0,.55);animation:np-sound-call 2.4s ease-in-out infinite}",
			".np-sound svg{width:40px;height:40px;flex:none}",
			".np-sound:hover{background:rgba(20,20,20,.9)}",
			".np-sound:focus-visible{outline:3px solid #f55d1a;outline-offset:3px}",
			".np-sound.np-on{height:56px;min-width:56px;padding:0;justify-content:center;animation:none;background:rgba(20,20,20,.55)}",
			".np-sound.np-on svg{width:28px;height:28px}",
			"@keyframes np-sound-call{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}",
			"@media (prefers-reduced-motion:reduce){.np-sound{animation:none}}",
		].join("");
		(document.head || document.documentElement).appendChild(style);
	}
	function sound(video) {
		if (video.dataset.npSound || video.hasAttribute("muted")) return;
		video.dataset.npSound = "1";
		soundStyle();
		video.muted = true;
		video.setAttribute("playsinline", "");
		// whatever plays it (the deck, a click on it), it stays silent until the person asks for its sound
		video.addEventListener("play", () => {
			if (!voiced.has(video)) video.muted = true;
		});
		const host = video.parentElement || document.body;
		if (getComputedStyle(host).position === "static") host.style.position = "relative";
		const button = document.createElement("button");
		button.type = "button";
		button.className = "np-sound";
		const draw = () => {
			const on = !video.muted;
			button.classList.toggle("np-on", on);
			button.innerHTML = on ? SOUND_ON : SOUND_OFF;
			if (!on) {
				const label = document.createElement("span");
				label.textContent = words.soundOn;
				button.appendChild(label);
			}
			button.setAttribute("aria-label", on ? words.soundOff : words.soundOn);
		};
		button.addEventListener("click", (event) => {
			event.preventDefault();
			event.stopPropagation();
			if (video.muted) {
				voiced.add(video);
				video.muted = false;
				if (video.paused) video.play().catch(() => {});
			} else {
				voiced.delete(video);
				video.muted = true;
			}
			draw();
		});
		host.appendChild(button);
		redraws.push(draw);
		draw();
		// on screen, it plays at once (silent); off screen, it stops
		if (window.IntersectionObserver) {
			new IntersectionObserver((entries) =>
				entries.forEach((entry) => {
					if (entry.isIntersecting && video.paused && !video.ended) video.play().catch(() => {});
					else if (!entry.isIntersecting && !video.paused) video.pause();
				}), { threshold: 0.5 }
			).observe(video);
		}
	}

	const scan = () => document.querySelectorAll("video").forEach((video) => { follow(video); sound(video); });
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
		if (data.source !== "np-viewer") return;
		if (data.type === "words") {
			words = Object.assign(words, data.words || {});
			redraws.forEach((draw) => draw());
			return;
		}
		if (data.type !== "go") return;
		if (window.Reveal && typeof window.Reveal.next === "function") {
			data.dir > 0 ? window.Reveal.next() : window.Reveal.prev();
		} else {
			const key = data.dir > 0 ? "ArrowRight" : "ArrowLeft";
			document.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
		}
	});
})();

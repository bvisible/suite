// //// Neoffice — added file (no upstream equivalent): the visitor's page of a shared presentation
// //// (suite/drive/presentation/). The e-mail, the code, the logo, then the presentation in a sandboxed frame; the frame's
// //// bridge (bridge.js) says which slide is on screen and how far the videos went, and this page counts the seconds the
// //// page is really looked at (visible, and touched in the last two minutes or a video playing) and sends them every 15 s.
// //// « A question? » asks about the slide on screen (maintenance#2337): Nora answers from the presentation, or the
// //// question goes to the person who answers for the link; the page follows the answer.
// //// The preview (/p/<token>/preview/<secret>, ours only) opens the presentation at once, without the e-mail and the
// //// code: no visit, so nothing is counted; a question gets what Nora would answer, and nothing is sent.
// //// A question can be dictated (our transcription, in Switzerland); the last slide is greeted with a little
// //// celebration and what one can do next (Jérémy, 09.11: « pour donner le truc un peu ludique »).
// //// The wheel turns the slides, one per gesture, and each stroke of the bar at the bottom goes to its slide (09.11).
// //// A code given with the link opens it too (« J'ai un code d'accès », enter_with_code), without the e-mail step.
(function () {
	"use strict";
	const config = window.npConfig || {};
	const S = config.strings || {};
	if (!config.isOpen) return;
	const preview = config.preview || null;
	// the logos of a link the preview opens in any state: the preview names its secret
	const logoQuery = preview ? "preview=" + encodeURIComponent(preview.secret) : "";

	const API = "/api/method/suite.drive.presentation.api.";
	const STORE = "np:" + config.token;
	const BEAT_MS = 15000;
	const IDLE_MS = 120000;
	const $ = (id) => document.getElementById(id);
	const format = (text, ...values) => values.reduce((out, value, i) => out.replace("{" + i + "}", value), text || "");

	let email = "";
	let visit = null;
	let current = 1;
	let total = 0;
	let furthest = 1;
	let lastActivity = Date.now();
	let playing = false;
	let pending = {};
	let videos = {};
	let frame = null;
	let live = false;

	function store() {
		try { return JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { return {}; }
	}
	function keep(values) {
		try { localStorage.setItem(STORE, JSON.stringify(Object.assign(store(), values))); } catch (e) { /* private window */ }
	}
	function browserId() {
		let id = store().browser;
		if (!id) {
			id = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)).replace(/-/g, "");
			keep({ browser: id });
		}
		return id;
	}

	async function call(method, args, keepalive) {
		const body = new URLSearchParams();
		Object.entries(args).forEach(([key, value]) => body.append(key, typeof value === "object" ? JSON.stringify(value) : value ?? ""));
		const headers = { Accept: "application/json", "Content-Type": "application/x-www-form-urlencoded" };
		if (config.csrfToken) headers["X-Frappe-CSRF-Token"] = config.csrfToken;
		const response = await fetch(API + method, { method: "POST", body, headers, keepalive: !!keepalive, credentials: "same-origin" });
		const data = await response.json().catch(() => ({}));
		if (!response.ok) throw new Error(S.error);
		return data.message || {};
	}

	function showError(id, text) {
		const el = $(id);
		el.textContent = text || "";
		el.hidden = !text;
	}

	// The logo at the top ----------------------------------------------------------------------------------------------
	if (config.hasBrand) {
		const img = document.createElement("img");
		img.src = "/p/" + config.token + "/brand" + (logoQuery ? "?" + logoQuery : "");
		img.alt = "";
		$("np-brand").appendChild(img);
	}

	// The e-mail -------------------------------------------------------------------------------------------------------
	const emailForm = $("np-email-form");
	if (emailForm) emailForm.addEventListener("submit", async (event) => {
		event.preventDefault();
		showError("np-email-error", "");
		const button = emailForm.querySelector("button");
		button.disabled = true;
		try {
			const result = await call("request_code", {
				token: config.token,
				email: emailForm.email.value,
				first_name: emailForm.first_name.value,
			});
			if (!result.ok) return showError("np-email-error", result.message);
			email = result.email;
			$("np-sent-to").textContent = format(S.sentTo, email);
			$("np-gate").hidden = true;
			$("np-code").hidden = false;
			digits()[0].focus();
		} catch (e) {
			showError("np-email-error", S.error);
		} finally {
			button.disabled = false;
		}
	});

	// The code ---------------------------------------------------------------------------------------------------------
	const digits = () => Array.from(($("np-digits") || document.createElement("div")).querySelectorAll("input"));
	digits().forEach((input, i, all) => {
		input.addEventListener("input", () => {
			input.value = input.value.replace(/\D/g, "").slice(-1);
			if (input.value && i < all.length - 1) all[i + 1].focus();
			check();
		});
		input.addEventListener("keydown", (event) => {
			if (event.key === "Backspace" && !input.value && i > 0) all[i - 1].focus();
		});
		input.addEventListener("paste", (event) => {
			const text = (event.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "").slice(0, 6);
			if (!text) return;
			event.preventDefault();
			text.split("").forEach((digit, k) => { if (all[k]) all[k].value = digit; });
			check();
		});
	});
	async function check() {
		const code = digits().map((input) => input.value).join("");
		if (code.length !== 6) return;
		showError("np-code-error", "");
		try {
			const result = await call("verify_code", { token: config.token, email, code, browser_id: browserId() });
			if (!result.ok) {
				showError("np-code-error", result.message);
				digits().forEach((input) => (input.value = ""));
				digits()[0].focus();
				return;
			}
			keep({ email, remember: result.remember });
			open(result);
		} catch (e) {
			showError("np-code-error", S.error);
		}
	}
	if (emailForm) {
		$("np-resend").addEventListener("click", () => {
			$("np-code").hidden = true;
			$("np-gate").hidden = false;
			emailForm.email.value = email;
			emailForm.requestSubmit();
		});
		$("np-other").addEventListener("click", () => {
			$("np-code").hidden = true;
			$("np-gate").hidden = false;
			emailForm.email.focus();
		});
	}

	// The code given with the link (Jérémy, 09.11): no e-mail, no code to wait for. The link may end in #code, which
	// opens the page on it. The code is never in the address: it would stay in the browser's history.
	const accessForm = $("np-access-form");
	function showAccess(on) {
		if (!accessForm) return;
		accessForm.hidden = !on;
		emailForm.hidden = on;
		$("np-have-code").hidden = on;
		$("np-code-by-email").hidden = !on;
		showError("np-access-error", "");
		(on ? accessForm.code : emailForm.email).focus();
	}
	if (accessForm) {
		$("np-have-code").addEventListener("click", () => showAccess(true));
		$("np-code-by-email").addEventListener("click", () => showAccess(false));
		accessForm.addEventListener("submit", async (event) => {
			event.preventDefault();
			showError("np-access-error", "");
			const button = accessForm.querySelector("button");
			button.disabled = true;
			try {
				const result = await call("enter_with_code", { token: config.token, code: accessForm.code.value, browser_id: browserId() });
				if (!result.ok) return showError("np-access-error", result.message);
				email = result.email;
				keep({ email, remember: result.remember });
				open(result);
			} catch (e) {
				showError("np-access-error", S.error);
			} finally {
				button.disabled = false;
			}
		});
		if (window.location.hash === "#code") showAccess(true);
	}

	// A browser where the code was given lately opens straight away ----------------------------------------------------
	const known = store();
	if (!preview && known.email && known.remember) {
		call("resume", { token: config.token, email: known.email, remember: known.remember, browser_id: browserId() })
			.then((result) => { if (result.ok) { email = known.email; open(result, true); } })
			.catch(() => {});
	}

	// The logo, then the presentation ----------------------------------------------------------------------------------
	function open(result, returning) {
		visit = result.visit;
		const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
		const introLogo = config.hasLogo ? "logo" : config.hasBrand ? "brand" : "";
		const hold = returning || !introLogo ? 0 : Math.max(0.6, config.introSeconds || 1.2) * 1000;
		$("np-paper").classList.add("np-leaving");
		const startPlayer = () => {
			$("np-intro").classList.remove("np-on");
			player(result);
			setTimeout(() => ($("np-intro").hidden = true), 500);
		};
		if (!hold) return setTimeout(startPlayer, 320);
		const intro = $("np-intro");
		const logo = $("np-intro-logo");
		logo.src = "/p/" + config.token + "/" + introLogo + "?play=" + Date.now() + (logoQuery ? "&" + logoQuery : "");
		intro.hidden = false;
		requestAnimationFrame(() => intro.classList.add("np-on"));
		setTimeout(startPlayer, reduced ? 600 : hold + 400);
	}

	function player(result) {
		const box = $("np-player");
		frame = $("np-frame");
		// once its document is there, the presentation takes the keys itself (its Home, End, F…)
		frame.addEventListener("load", () => {
			// the words of the frame's sound buttons, in the page's language
			frame.contentWindow.postMessage({ source: "np-viewer", type: "words", words: { soundOn: S.soundOn, soundOff: S.soundOff } }, "*");
			if (typing()) return;
			try { frame.contentWindow.focus(); } catch (e) { frame.focus(); }
		});
		frame.src = result.content;
		live = true;
		box.hidden = false;
		requestAnimationFrame(() => box.classList.add("np-on"));
		$("np-forward").hidden = !result.can_forward;
		setupQuestions(result.questions);
		setInterval(tick, 1000);
		setInterval(beat, BEAT_MS);
		frame.focus();
	}

	// What the frame says ----------------------------------------------------------------------------------------------
	window.addEventListener("message", (event) => {
		if (!frame || event.source !== frame.contentWindow) return;
		const data = event.data || {};
		if (data.source !== "np-bridge") return;
		if (data.type === "slide") {
			current = Math.max(1, parseInt(data.index, 10) || 1);
			total = Math.max(total, parseInt(data.total, 10) || 0);
			furthest = Math.max(furthest, current);
			lastActivity = Date.now();
			draw();
			drawWhere();
		} else if (data.type === "video") {
			const percent = Math.max(0, Math.min(100, Math.round(data.percent || 0)));
			videos[data.src] = Math.max(videos[data.src] || 0, percent);
			playing = !!data.playing;
		} else if (data.type === "activity") {
			lastActivity = Date.now();
		} else if (data.type === "wheel") {
			wheel(data.dx, data.dy, data.mode);
		}
	});

	function draw() {
		const bar = $("np-progress");
		// each stroke is a slide: a click goes to it (Jérémy, 09.11: « cliquer sur les bulles pour sauter à une page »)
		if (bar.children.length !== total) {
			bar.innerHTML = "";
			for (let i = 0; i < total; i++) {
				const cell = document.createElement("button");
				cell.type = "button";
				cell.title = format(S.slideN, i + 1);
				cell.setAttribute("aria-label", cell.title);
				cell.appendChild(document.createElement("i"));
				cell.addEventListener("click", () => goToSlide(i + 1));
				bar.appendChild(cell);
			}
		}
		Array.from(bar.children).forEach((cell, i) => {
			cell.firstChild.className = i + 1 === current ? "np-now" : i + 1 <= furthest ? "np-seen" : "";
			if (i + 1 === current) cell.setAttribute("aria-current", "step");
			else cell.removeAttribute("aria-current");
		});
		$("np-count").innerHTML = "";
		const now = document.createElement("b");
		now.textContent = String(current);
		$("np-count").append(now, " / " + (total || "–"));
		celebrate();
	}

	// The last slide ----------------------------------------------------------------------------------------------------
	let celebrated = false;
	function celebrate() {
		const end = $("np-end");
		if (current < total && !end.hidden) hideEnd();
		if (celebrated || total < 2 || current !== total) return;
		celebrated = true;
		$("np-end-ask").hidden = !(asking && asking.enabled);
		$("np-end-forward").hidden = $("np-forward").hidden;
		end.hidden = false;
		requestAnimationFrame(() => end.classList.add("np-on"));
		if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) confetti();
	}
	function hideEnd() {
		const end = $("np-end");
		end.classList.remove("np-on");
		setTimeout(() => (end.hidden = true), 380);
	}
	$("np-end-close").addEventListener("click", hideEnd);
	$("np-end-ask").addEventListener("click", () => { hideEnd(); toggleAsk(true); });
	$("np-end-forward").addEventListener("click", () => { hideEnd(); $("np-forward").click(); });

	// The design system's warm colours, falling for two and a half seconds over the stage.
	function confetti() {
		const canvas = $("np-confetti");
		const box = $("np-player").getBoundingClientRect();
		const ratio = window.devicePixelRatio || 1;
		canvas.width = box.width * ratio;
		canvas.height = box.height * ratio;
		canvas.hidden = false;
		const ctx = canvas.getContext("2d");
		ctx.scale(ratio, ratio);
		const colours = ["#f55d1a", "#ffb599", "#c2723f", "#fffdf8", "#aa3700"];
		const bits = Array.from({ length: 140 }, () => ({
			x: box.width / 2 + (Math.random() - 0.5) * box.width * 0.5,
			y: box.height * 0.42,
			vx: (Math.random() - 0.5) * 14,
			vy: -Math.random() * 15 - 5,
			size: 5 + Math.random() * 7,
			spin: Math.random() * Math.PI,
			turn: (Math.random() - 0.5) * 0.35,
			colour: colours[Math.floor(Math.random() * colours.length)],
		}));
		const started = performance.now();
		(function frameStep(now) {
			const t = now - started;
			ctx.clearRect(0, 0, box.width, box.height);
			ctx.globalAlpha = Math.max(0, 1 - Math.max(0, t - 1800) / 700);
			bits.forEach((b) => {
				b.vy += 0.42;
				b.vx *= 0.985;
				b.x += b.vx;
				b.y += b.vy;
				b.spin += b.turn;
				ctx.save();
				ctx.translate(b.x, b.y);
				ctx.rotate(b.spin);
				ctx.fillStyle = b.colour;
				ctx.fillRect(-b.size / 2, -b.size / 4, b.size, b.size / 2);
				ctx.restore();
			});
			if (t < 2500) requestAnimationFrame(frameStep);
			else canvas.hidden = true;
		})(started);
	}

	// The seconds really looked at ---------------------------------------------------------------------------------------
	["pointermove", "keydown", "touchstart", "wheel", "click"].forEach((name) =>
		window.addEventListener(name, () => (lastActivity = Date.now()), { passive: true })
	);
	function tick() {
		if (document.visibilityState !== "visible") return;
		if (!playing && Date.now() - lastActivity > IDLE_MS) return;
		pending[current] = (pending[current] || 0) + 1;
	}
	function beat(final) {
		if (!visit) return;
		const seconds = pending;
		pending = {};
		const sent = Object.keys(seconds).length || Object.keys(videos).length;
		if (!sent && !final) return;
		call("track", { visit, beat: { seconds, slide: current, total, videos } }, true).catch(() => {
			Object.entries(seconds).forEach(([k, v]) => (pending[k] = (pending[k] || 0) + v));
		});
	}
	document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") beat(true); });
	window.addEventListener("pagehide", () => beat(true));

	// The controls -----------------------------------------------------------------------------------------------------
	const go = (dir) => frame && frame.contentWindow.postMessage({ source: "np-viewer", type: "go", dir }, "*");
	// the bridge only turns one slide at a time (bridge.js): as many turns as slides to the one asked
	function goToSlide(slide) {
		const steps = Math.max(-80, Math.min(80, slide - current));
		for (let i = 0; i < Math.abs(steps); i++) go(Math.sign(steps));
		// on a phone the panel covers the slide: it steps aside to show it
		if (window.matchMedia("(max-width: 760px)").matches) toggleAsk(false);
	}
	$("np-prev").addEventListener("click", () => go(-1));
	$("np-next").addEventListener("click", () => go(1));

	// The wheel turns the slides, one per gesture, as in a slide show (Jérémy, 09.11: « scroller pour défiler, comme en
	// PowerPoint »). A wheel's notch is a gesture; a trackpad's swipe is many small events and then its momentum, which
	// turns nothing more. The wheel inside the presentation comes from the bridge (bridge.js), unless what is under it
	// scrolls.
	const WHEEL_STEP = 40;
	let wheelSum = 0;
	let wheelTurnAt = 0;
	let wheelLastAt = 0;
	function wheel(dx, dy, mode) {
		if (!live) return;
		const unit = mode === 1 ? 40 : mode === 2 ? 800 : 1;
		const delta = (Math.abs(dx) > Math.abs(dy) ? dx : dy) * unit;
		const now = Date.now();
		const sameGesture = now - wheelLastAt < 200;
		wheelLastAt = now;
		if (now - wheelTurnAt < (sameGesture ? 1500 : 350)) return;
		if (!sameGesture) wheelSum = 0;
		wheelSum += delta || 0;
		if (Math.abs(wheelSum) < WHEEL_STEP) return;
		go(wheelSum > 0 ? 1 : -1);
		wheelSum = 0;
		wheelTurnAt = now;
	}
	$("np-stage").addEventListener("wheel", (event) => {
		if (event.ctrlKey) return; // a pinch zooms
		event.preventDefault();
		wheel(event.deltaX, event.deltaY, event.deltaMode);
	}, { passive: false });
	// The person types in a field on screen (the question, the forward dialog); a field left focused but hidden (the
	// code's last digit) is not typing.
	const typing = () => {
		const el = document.activeElement;
		if (!el || !(["TEXTAREA", "INPUT", "SELECT"].includes(el.tagName) || el.isContentEditable)) return false;
		return !el.closest("[hidden]");
	};
	document.addEventListener("keydown", (event) => {
		if (!live || $("np-forward-dialog").open) return;
		if (event.key === "Escape" && asking && !$("np-ask").hidden) return toggleAsk(false);
		if (typing() || event.metaKey || event.ctrlKey || event.altKey) return;
		// A key that reaches this page did not reach the presentation, even while its frame is the active element:
		// a frame focused before its document loaded keeps the keys out of it. This page turns the slide then.
		if (["ArrowRight", "PageDown", " "].includes(event.key)) { event.preventDefault(); go(1); }
		if (["ArrowLeft", "PageUp"].includes(event.key)) { event.preventDefault(); go(-1); }
	});
	$("np-full").addEventListener("click", () => {
		const box = $("np-player");
		if (document.fullscreenElement) document.exitFullscreen();
		else if (box.requestFullscreen) box.requestFullscreen();
	});

	// Forward to a colleague -------------------------------------------------------------------------------------------
	const dialog = $("np-forward-dialog");
	const forwardForm = $("np-forward-form");
	$("np-forward").addEventListener("click", () => {
		forwardForm.reset();
		showError("np-forward-error", "");
		$("np-forward-ok").hidden = true;
		$("np-forward-send").hidden = false;
		dialog.showModal();
	});
	$("np-forward-cancel").addEventListener("click", () => dialog.close());
	forwardForm.addEventListener("submit", async (event) => {
		event.preventDefault();
		showError("np-forward-error", "");
		const button = $("np-forward-send");
		if (preview) {
			// the preview sends nothing: it only shows the gesture
			$("np-forward-ok").textContent = S.previewNotSent;
			$("np-forward-ok").hidden = false;
			button.hidden = true;
			return setTimeout(() => dialog.close(), 2200);
		}
		button.disabled = true;
		try {
			const result = await call("forward", {
				visit,
				email: forwardForm.email.value,
				first_name: forwardForm.first_name.value,
				message: forwardForm.message.value,
			});
			if (!result.ok) return showError("np-forward-error", result.message);
			$("np-forward-ok").hidden = false;
			button.hidden = true;
			setTimeout(() => dialog.close(), 2200);
		} catch (e) {
			showError("np-forward-error", S.error);
		} finally {
			button.disabled = false;
		}
	});
	// A question on the slide on screen ---------------------------------------------------------------------------------
	let asking = null;
	let thread = [];
	let askedAt = 0;
	let polling = null;
	const el = (tag, cls, text) => {
		const node = document.createElement(tag);
		if (cls) node.className = cls;
		if (text !== undefined) node.textContent = text;
		return node;
	};
	const orb = () => {
		const img = el("img", "np-orb-small");
		img.src = "/assets/nora/images/nora-orb.svg";
		img.alt = "";
		img.onerror = () => img.remove();
		return img;
	};

	function setupQuestions(settings) {
		asking = settings || {};
		if (!asking.enabled) return;
		const form = $("np-ask-form");
		$("np-ask-open").hidden = false;
		setupDictation();
		$("np-ask-sub").textContent = asking.nora ? format(S.askSubNora, asking.answeredBy) : format(S.askSubPerson, asking.answeredBy);
		$("np-ask-open").addEventListener("click", () => toggleAsk());
		$("np-ask-close").addEventListener("click", () => toggleAsk(false));
		form.addEventListener("submit", sendQuestion);
		form.question.addEventListener("keydown", (event) => {
			if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
				event.preventDefault();
				form.requestSubmit();
			}
		});
		loadThread();
	}

	function toggleAsk(force) {
		const panel = $("np-ask");
		const show = typeof force === "boolean" ? force : panel.hidden;
		panel.hidden = !show;
		$("np-player").classList.toggle("np-asking", show);
		$("np-ask-open").setAttribute("aria-pressed", String(show));
		if (show) {
			drawWhere();
			drawThread();
			loadThread();
			$("np-ask-form").question.focus();
		} else if (frame) {
			frame.focus();
		}
	}

	function drawWhere() {
		if (!asking || !asking.enabled || $("np-ask").hidden) return;
		const title = (asking.slides || [])[current - 1] || "";
		$("np-ask-where").textContent = title ? format(S.onSlideTitled, current, title) : format(S.onSlide, current);
	}

	function drawThread() {
		const box = $("np-ask-thread");
		box.innerHTML = "";
		if (!thread.length) {
			box.append(el("p", "np-ask-hint", asking.nora ? S.askHint : format(S.askHintPerson, asking.answeredBy)));
			return;
		}
		thread.forEach((q) => {
			box.append(el("div", "np-q", q.question));
			const reply = el("div", "np-a");
			const body = el("div", "np-a-body");
			if (q.status === "Asked") {
				reply.append(orb());
				body.append(el("p", "np-a-text np-thinking", S.askThinking));
			} else if (q.status === "Answered by Nora") {
				reply.append(orb());
				body.append(el("p", "np-a-text", q.answer));
				if ((q.sources || []).length) {
					const chips = el("div", "np-chips");
					q.sources.forEach((label, i) => {
						// a slide's chip turns the deck to it; a kept answer's chip only names who said it
						const slide = (q.slides || [])[i];
						const link = (q.links || [])[i];
						if (link) {
							// a page of the site or of the manual opens beside the presentation
							const a = el("a", "np-chip", label);
							a.href = link;
							a.target = "_blank";
							a.rel = "noopener noreferrer";
							return chips.append(a);
						}
						if (!slide) return chips.append(el("span", "np-chip", label));
						const chip = el("button", "np-chip np-chip-go", label);
						chip.type = "button";
						chip.addEventListener("click", () => goToSlide(slide));
						chips.append(chip);
					});
					body.append(chips);
				}
			} else if (q.status === "Preview") {
				reply.append(orb());
				body.append(el("p", "np-a-text", format(S.previewWouldForward, asking.answeredBy)));
			} else if (q.status === "Answered") {
				reply.classList.add("np-a-person");
				body.append(el("p", "np-a-by", format(S.answerOf, q.by)), el("p", "np-a-text", q.answer));
			} else {
				reply.append(orb());
				const text = asking.nora ? S.askForwarded : S.askForwardedPerson;
				body.append(el("p", "np-a-text", format(text, asking.answeredBy, email)));
				const pill = el("span", "np-pill");
				pill.append(el("i"), format(S.forwardedPill, asking.answeredBy));
				body.append(pill);
			}
			reply.append(body);
			box.append(reply);
		});
		box.scrollTop = box.scrollHeight;
	}

	async function loadThread() {
		if (!visit) return;
		try {
			const result = await call("questions", { visit });
			if (result.ok) {
				thread = result.questions || [];
				drawThread();
			}
		} catch (e) {
			/* the next look will try again */
		}
		schedule();
	}

	function schedule() {
		clearTimeout(polling);
		if (thread.some((q) => q.status === "Asked") && Date.now() - askedAt < 120000) polling = setTimeout(loadThread, 2500);
	}

	async function sendQuestion(event) {
		event.preventDefault();
		const form = $("np-ask-form");
		const text = form.question.value.trim();
		if (!text) return;
		showError("np-ask-error", "");
		const button = form.querySelector("button");
		button.disabled = true;
		if (preview) return previewQuestion(form, button, text);
		try {
			const result = await call("ask", { visit, question: text, slide: current });
			if (!result.ok) return showError("np-ask-error", result.message);
			form.question.value = "";
			// a greeting, a thank-you, a goodbye: Nora answers at once, and nothing was recorded (questions.small_talk)
			if (result.reply) {
				thread.push({ slide: current, question: text, status: "Answered by Nora", answer: result.reply, sources: [] });
				drawThread();
				return;
			}
			thread.push({ name: result.question, slide: current, question: text, status: "Asked" });
			askedAt = Date.now();
			drawThread();
			schedule();
		} catch (e) {
			showError("np-ask-error", S.error);
		} finally {
			button.disabled = false;
		}
	}

	// In the preview, Nora answers as she would answer a visitor, and nothing is recorded or sent (api.preview_ask).
	async function previewQuestion(form, button, text) {
		const item = { slide: current, question: text, status: "Asked" };
		thread.push(item);
		form.question.value = "";
		drawThread();
		try {
			const result = await call("preview_ask", { token: config.token, preview: preview.secret, question: text, slide: current });
			if (!result.ok) {
				thread.splice(thread.indexOf(item), 1);
				return showError("np-ask-error", result.message);
			}
			if (result.sure) Object.assign(item, { status: "Answered by Nora", answer: result.answer, sources: result.sources, slides: result.slides, links: result.links });
			else item.status = "Preview";
		} catch (e) {
			thread.splice(thread.indexOf(item), 1);
			showError("np-ask-error", S.error);
		} finally {
			drawThread();
			button.disabled = false;
		}
	}

	// Dictation: a tap listens, a second tap (or a minute) stops; our transcription writes the words after what was
	// typed, and nothing is sent: the person reads them first.
	const DICTATION_MS = 60000;
	const AUDIO_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
	let take = null;
	function setupDictation() {
		const mic = $("np-ask-mic");
		const can = asking.dictation && window.MediaRecorder && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
		if (!can || mic.dataset.ready) return;
		mic.dataset.ready = "1";
		mic.hidden = false;
		mic.addEventListener("click", () => (take ? stopDictation() : startDictation()));
		document.addEventListener("visibilitychange", () => { if (document.hidden && take) stopDictation(true); });
	}
	function dictationState(state, seconds) {
		const mic = $("np-ask-mic");
		const line = $("np-ask-state");
		mic.classList.toggle("np-listening", state === "listening");
		mic.classList.toggle("np-writing", state === "writing");
		mic.setAttribute("aria-label", state === "listening" ? S.stopDictation : S.dictate);
		mic.title = mic.getAttribute("aria-label");
		line.hidden = state === "idle";
		line.textContent = state === "listening" ? format(S.listening, seconds || 0) : state === "writing" ? S.writing : "";
	}
	async function startDictation() {
		showError("np-ask-error", "");
		const t = { chunks: [], started: Date.now(), cancelled: false };
		take = t;
		dictationState("listening", 0);
		try {
			t.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			if (take !== t) return release(t);
			const type = AUDIO_TYPES.find((each) => MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(each));
			t.rec = new MediaRecorder(t.stream, type ? { mimeType: type } : undefined);
			t.type = t.rec.mimeType || type || "audio/webm";
			t.rec.ondataavailable = (e) => { if (e.data && e.data.size) t.chunks.push(e.data); };
			t.rec.onstop = () => writeDown(t);
			t.rec.start();
			t.clock = setInterval(() => dictationState("listening", Math.floor((Date.now() - t.started) / 1000)), 1000);
			t.limit = setTimeout(() => stopDictation(), DICTATION_MS);
		} catch (e) {
			release(t);
			if (take === t) take = null;
			dictationState("idle");
			showError("np-ask-error", S.noMicrophone);
		}
	}
	function stopDictation(cancel) {
		const t = take;
		if (!t) return;
		t.cancelled = !!cancel;
		if (t.rec && t.rec.state !== "inactive") return t.rec.stop();
		take = null;
		release(t);
		dictationState("idle");
	}
	function release(t) {
		clearInterval(t.clock);
		clearTimeout(t.limit);
		(t.stream ? t.stream.getTracks() : []).forEach((track) => track.stop());
	}
	async function writeDown(t) {
		release(t);
		if (take === t) take = null;
		if (t.cancelled || !t.chunks.length) return dictationState("idle");
		dictationState("writing");
		const body = new FormData();
		body.append("file", new Blob(t.chunks, { type: t.type }), "question." + (/mp4/.test(t.type) ? "m4a" : "webm"));
		if (preview) {
			body.append("token", config.token);
			body.append("preview", preview.secret);
		} else {
			body.append("visit", visit || "");
		}
		try {
			const headers = { Accept: "application/json" };
			if (config.csrfToken) headers["X-Frappe-CSRF-Token"] = config.csrfToken;
			const response = await fetch(API + "transcribe", { method: "POST", body, headers, credentials: "same-origin" });
			const result = ((await response.json().catch(() => ({}))) || {}).message || {};
			const text = String(result.text || "").trim();
			if (!response.ok || !result.ok) throw new Error(result.message || S.error);
			if (!text) throw new Error(S.heardNothing);
			const field = $("np-ask-form").question;
			field.value = (field.value.trim() ? field.value.trim() + " " : "") + text;
			field.focus();
		} catch (e) {
			showError("np-ask-error", (e && e.message) || S.error);
		} finally {
			dictationState("idle");
		}
	}

	if (preview) open(preview);
})();

// //// Neoffice — added file (no upstream equivalent): the visitor's page of a shared presentation
// //// (suite/drive/presentation/). The e-mail, the code, the logo, then the presentation in a sandboxed frame; the frame's
// //// bridge (bridge.js) says which slide is on screen and how far the videos went, and this page counts the seconds the
// //// page is really looked at (visible, and touched in the last two minutes or a video playing) and sends them every 15 s.
// //// « A question? » asks about the slide on screen (maintenance#2337): Nora answers from the presentation, or the
// //// question goes to the person who answers for the link; the page follows the answer.
(function () {
	"use strict";
	const config = window.npConfig || {};
	const S = config.strings || {};
	if (!config.isOpen) return;

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
		img.src = "/p/" + config.token + "/brand";
		img.alt = "";
		$("np-brand").appendChild(img);
	}

	// The e-mail -------------------------------------------------------------------------------------------------------
	const emailForm = $("np-email-form");
	emailForm.addEventListener("submit", async (event) => {
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
	const digits = () => Array.from($("np-digits").querySelectorAll("input"));
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

	// A browser where the code was given lately opens straight away ----------------------------------------------------
	const known = store();
	if (known.email && known.remember) {
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
		logo.src = "/p/" + config.token + "/" + introLogo + "?play=" + Date.now();
		intro.hidden = false;
		requestAnimationFrame(() => intro.classList.add("np-on"));
		setTimeout(startPlayer, reduced ? 600 : hold + 400);
	}

	function player(result) {
		const box = $("np-player");
		frame = $("np-frame");
		frame.src = result.content;
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
		}
	});

	function draw() {
		const bar = $("np-progress");
		if (bar.children.length !== total) {
			bar.innerHTML = "";
			for (let i = 0; i < total; i++) bar.appendChild(document.createElement("i"));
		}
		Array.from(bar.children).forEach((cell, i) => {
			cell.className = i + 1 === current ? "np-now" : i + 1 <= furthest ? "np-seen" : "";
		});
		$("np-count").innerHTML = "";
		const now = document.createElement("b");
		now.textContent = String(current);
		$("np-count").append(now, " / " + (total || "–"));
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
	$("np-prev").addEventListener("click", () => go(-1));
	$("np-next").addEventListener("click", () => go(1));
	document.addEventListener("keydown", (event) => {
		if (!visit || document.activeElement === frame || $("np-forward-dialog").open) return;
		if (["TEXTAREA", "INPUT"].includes((document.activeElement || {}).tagName)) return;
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
					q.sources.forEach((label) => chips.append(el("span", "np-chip", label)));
					body.append(chips);
				}
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
		try {
			const result = await call("ask", { visit, question: text, slide: current });
			if (!result.ok) return showError("np-ask-error", result.message);
			form.question.value = "";
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
})();

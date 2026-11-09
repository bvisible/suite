// //// Neoffice — added file (no upstream equivalent): the staff's side of a shared presentation: copy or send the link,
// //// withdraw it, and see what each person saw (suite/drive/presentation/api.py get_stats); answer the questions asked
// //// on it, see what Nora knows for it and try her as a visitor (maintenance#2337). Drawn as the design plan of 06.11
// //// draws the record (« Présentations partagées et suivies — écrans »), with the design system's tokens
// //// (suite/public/presentation/link-form.css). One head (Jérémy, 09.11: « ne me fais pas des choses à double »): what
// //// waits and what was seen is said at the top right of the form's own head, and the tabs no longer repeat it; the
// //// preview link, ours only, opens the presentation without a code and counts nothing. « Give an Access Code » makes a
// //// code for one person, given with the link (09.11).
const NP_FORM_CSS = "/assets/suite/presentation/link-form.css?v=6";
const NP_MODES = {
	nora: "Nora Answers, Else Forwards",
	forward: "Forward Every Question",
	none: "No Questions",
};

// The form's head says it, at its top right (frappe's form hero, its detail block, fed by the controller's onload):
// the question that waits, found in seconds, then who watched and to whom the link went. Clicking a line opens its tab.
if (frappe.ui.form.add_hero_detail && !frappe.ui.form.__np_link_head) {
	frappe.ui.form.__np_link_head = true;
	frappe.ui.form.add_hero_detail("Presentation Link", (frm) => link_head(frm));
}

frappe.ui.form.on("Presentation Link", {
	setup(frm) {
		// before the head is drawn: it is placed by this stylesheet
		load_form_css();
		frm.$wrapper.addClass("np-link-form");
	},
	refresh(frm) {
		for (const field of ["stats_html", "questions_html", "nora_sources_html"]) frm.get_field(field).$wrapper.empty();
		if (frm.is_new()) {
			open_tab(frm, "settings_tab");
			return;
		}
		if (frm.doc.status !== "Withdrawn") {
			frm.add_custom_button(__("Send the Link"), () => send_link(frm)).addClass("btn-primary");
			if (frm.doc.preview_url) frm.add_custom_button(__("Preview"), () => window.open(frm.doc.preview_url, "_blank", "noopener"));
			frm.add_custom_button(__("Copy the Link"), () => frappe.utils.copy_to_clipboard(frm.doc.url));
			frm.add_custom_button(__("Give an Access Code"), () => give_access_code(frm));
			if (frm.doc.preview_url) {
				frm.add_custom_button(__("Copy the Preview Link"), () => frappe.utils.copy_to_clipboard(frm.doc.preview_url), __("More"));
				frm.add_custom_button(__("New Preview Link"), () => new_preview(frm, true), __("More"));
			}
			frm.add_custom_button(
				__("Withdraw"),
				() =>
					frappe.confirm(__("The link will open nothing any more. The visits stay."), () =>
						frm.set_value("status", "Withdrawn").then(() => frm.save())
					),
				__("More")
			);
		}
		// a link made before the preview existed gets its preview link once
		if (!frm.doc.preview_url && frm.perm[0] && frm.perm[0].write && frm.__np_preview_made !== frm.doc.name) {
			frm.__np_preview_made = frm.doc.name;
			new_preview(frm, false);
		}
		load_form_css();
		frappe
			.call("suite.drive.presentation.api.get_stats", { name: frm.doc.name })
			.then((r) => render_stats(frm, r.message || {}));
		frappe.call("suite.drive.presentation.api.get_questions", { name: frm.doc.name }).then((r) => {
			render_questions(frm, r.message || {});
			render_sources(frm, r.message || {});
		});
		open_asked_tab(frm);
	},
});

// The « Reply » button of the e-mail that forwards a question opens the record on its Questions tab
// (`?tab=questions`, suite/drive/presentation/questions.py), once per opening of the record.
function open_asked_tab(frm) {
	const wanted = new URLSearchParams(window.location.search).get("tab");
	if (!wanted || frm.__np_tab_opened === frm.doc.name) return;
	frm.__np_tab_opened = frm.doc.name;
	open_tab(frm, `${wanted}_tab`);
}

// Once per page: frappe.require reads `?v=` as the file's type and loads nothing, so the stylesheet is linked here,
// its version in the address so a new one passes the browser's cache.
function load_form_css() {
	if (document.getElementById("np-link-form-css")) return;
	const link = document.createElement("link");
	link.id = "np-link-form-css";
	link.rel = "stylesheet";
	link.href = NP_FORM_CSS;
	document.head.appendChild(link);
}

function open_tab(frm, fieldname) {
	const tab = (frm.layout.tabs || []).find((t) => t.df.fieldname === fieldname);
	if (tab) tab.set_active();
}

// A new preview link: the former one opens nothing any more (the first one, for a link made before the preview).
function new_preview(frm, ask) {
	const make = () =>
		frappe.call({ method: "suite.drive.presentation.api.new_preview", args: { name: frm.doc.name } }).then(() => {
			if (ask) frappe.show_alert({ message: __("A new preview link is ready."), indicator: "green" });
			frm.reload_doc();
		});
	if (ask) frappe.confirm(__("The former preview link will open nothing any more."), make);
	else make();
}

function link_head(frm) {
	const h = (frm.doc.__onload || {}).np_header;
	if (frm.is_new() || !h) return null;
	const lines = [];
	if (h.question) {
		lines.push({ text: `« ${h.question.text} » · ${h.question.who}`, title: __("Answer it"), run: () => open_tab(frm, "questions_tab") });
	}
	if (h.people) {
		const watched = [h.people === 1 ? __("1 person") : __("{0} people", [h.people]), __("{0} on screen", [duration(h.seconds)])];
		if (h.video) watched.push(__("video seen to {0} %", [h.video]));
		lines.push({ icon: "user", text: watched.join(" · "), run: () => open_tab(frm, "seen_tab") });
	} else {
		lines.push({ icon: "user", text: __("Nobody has entered yet.") });
	}
	if (!h.waiting && h.questions) {
		lines.push({ text: h.questions === 1 ? __("1 question, answered") : __("{0} questions, all answered", [h.questions]), run: () => open_tab(frm, "questions_tab") });
	}
	// a link never sent says it by its status (« Draft ») already
	const sent = h.sent_to || [];
	if (sent.length) lines.push({ icon: "send", text: __("Sent to {0}", [sent.join(", ")]), title: sent.join("\n") });
	const label = h.waiting ? (h.waiting === 1 ? __("A question waits for you") : __("{0} questions wait for you", [h.waiting])) : "";
	return { label, lines };
}

function send_link(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Send the Link"),
		fields: [
			{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("E-mail Address"), reqd: 1 },
			{ fieldname: "first_name", fieldtype: "Data", label: __("First Name") },
			{ fieldname: "message", fieldtype: "Small Text", label: __("A Note") },
		],
		primary_action_label: __("Send"),
		primary_action(values) {
			frappe
				.call("suite.drive.presentation.api.send_link", { name: frm.doc.name, ...values })
				.then(() => {
					dialog.hide();
					frappe.show_alert({ message: __("The link is on its way."), indicator: "green" });
					frm.reload_doc();
				});
		},
	});
	dialog.show();
}

// A code given with the link to one person (Jérémy, 09.11: « lui donner un code »): she opens the link, which ends in
// #code, types the code and enters, without an e-mail to wait for. The code is shown here once; only its fingerprint
// is kept (suite/drive/presentation/api.py new_access_code).
function give_access_code(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Give an Access Code"),
		fields: [
			{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("E-mail Address"), reqd: 1 },
			{ fieldname: "first_name", fieldtype: "Data", label: __("First Name") },
			{
				fieldname: "note",
				fieldtype: "HTML",
				options: `<p class="text-muted small">${esc(__("The code opens the link for this person only. It is shown once: copy it into your message."))}</p>`,
			},
		],
		primary_action_label: __("Create the Code"),
		primary_action(values) {
			frappe.call("suite.drive.presentation.api.new_access_code", { name: frm.doc.name, ...values }).then((r) => {
				dialog.hide();
				show_access_code(r.message || {});
				frm.reload_doc();
			});
		},
	});
	dialog.show();
}

function show_access_code(given) {
	const until = frappe.datetime.str_to_user(given.valid_until).split(" ")[0];
	const sentence = __("Open {0} and enter the access code {1}. It is valid until {2}.", [given.url, given.code, until]);
	const dialog = new frappe.ui.Dialog({
		title: __("The Code for {0}", [given.email]),
		fields: [
			{
				fieldname: "code",
				fieldtype: "HTML",
				options: `<div class="np-access-code">
					<div class="np-access-code-value">${esc(given.code)}</div>
					<p>${esc(__("Valid until {0}. It will not be shown again.", [until]))}</p>
					<p class="np-access-code-sentence">${esc(sentence)}</p>
				</div>`,
			},
		],
		primary_action_label: __("Copy the Sentence"),
		primary_action() {
			frappe.utils.copy_to_clipboard(sentence);
		},
		secondary_action_label: __("Copy the Code"),
		secondary_action() {
			frappe.utils.copy_to_clipboard(given.code);
		},
	});
	dialog.show();
}

// Small pieces ------------------------------------------------------------------------------------------------------------
const esc = (value) => frappe.utils.escape_html(value == null ? "" : String(value));

function duration(seconds) {
	seconds = Math.round(seconds || 0);
	if (seconds < 60) return __("{0} s", [seconds]);
	if (seconds < 3600) {
		const rest = seconds % 60;
		return rest && seconds < 600 ? __("{0} min {1}", [Math.floor(seconds / 60), String(rest).padStart(2, "0")]) : __("{0} min", [Math.round(seconds / 60)]);
	}
	return __("{0} h {1}", [Math.floor(seconds / 3600), String(Math.round((seconds % 3600) / 60)).padStart(2, "0")]);
}

function pill(text, tone) {
	return `<span class="np-pill${tone ? " np-" + tone : ""}">${esc(text)}</span>`;
}

function orb() {
	const dark = document.documentElement.getAttribute("data-theme") === "dark";
	return `<img class="np-orb" src="/assets/nora/images/nora-orb${dark ? "-dark" : ""}.svg" alt="" onerror="this.remove()">`;
}

const DEVICE_IN_A_SENTENCE = () => ({ Computer: __("a computer"), Phone: __("a phone"), Tablet: __("a tablet") });
const DEVICE_NAME = () => ({
	Computer: __("Computer", null, "device"),
	Phone: __("Phone", null, "device"),
	Tablet: __("Tablet", null, "device"),
});

function day_of(value) {
	const day = frappe.datetime.str_to_obj(value);
	const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	const diff = Math.round((new Date(day.getFullYear(), day.getMonth(), day.getDate()) - today) / 86400000);
	if (diff === 0) return __("Today");
	if (diff === -1) return __("Yesterday");
	return frappe.datetime.str_to_user(String(value).slice(0, 10));
}

function hour_of(value) {
	const date = frappe.datetime.str_to_obj(value);
	return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

// What they saw (the head above says how many and how long) ---------------------------------------------------------------
function render_stats(frm, data) {
	const wrapper = frm.get_field("stats_html").$wrapper;
	const viewers = data.viewers || [];
	const count = data.slide_count || 0;
	wrapper.html(`
		<div class="np-desk">
			${viewers.length ? `<div class="np-row">${chart_card(data, viewers)}${log_card(data)}</div>` : ""}
			${viewers.length || (data.invited || []).length ? people_table(data, viewers, count) : `<div class="np-card"><div class="np-empty">${esc(__("When someone enters, the time spent on each slide and what each person saw appear here."))}</div></div>`}
		</div>`);
	bind_chart(wrapper, data);
}

function chart_card(data, viewers) {
	const count = data.slide_count || 0;
	if (!count) return "";
	const per = data.per_slide || {};
	const seconds = Array.from({ length: count }, (_, i) => per[String(i + 1)] || 0);
	const top = Math.max(1, ...seconds);
	const ranked = seconds
		.map((s, i) => [s, i])
		.filter(([s]) => s > 0)
		.sort((a, b) => b[0] - a[0]);
	const heaviest = new Set(ranked.slice(0, 3).map(([, i]) => i));
	const labelled = new Set(ranked.slice(0, 2).map(([, i]) => i));
	const titles = data.slide_titles || [];
	const PLOT = 190;
	const bars = seconds
		.map((s, i) => {
			const height = Math.max(2, Math.round((s / top) * PLOT));
			const label = labelled.has(i) ? `<em style="bottom:${height + 6}px">${esc(duration(s))}</em>` : "";
			const name = __("Slide {0}: {1}", [i + 1, duration(s)]);
			return `<button type="button" class="np-bar${heaviest.has(i) ? " np-top" : ""}" data-slide="${i + 1}" data-seconds="${s}" aria-label="${esc(name)}"><i style="height:${height}px"></i>${label}</button>`;
		})
		.join("");
	return `
		<div class="np-card np-wide">
			<div class="np-card-head">
				<h2>${esc(__("The time spent on each slide"))}</h2>
				<span class="np-note">${esc(__("Everyone together · only the time the page was really looked at counts"))}</span>
			</div>
			<div class="np-chart">
				<div class="np-grid" style="top:${230 - 1 - PLOT}px"></div>
				<div class="np-grid" style="top:${230 - 1 - PLOT / 2}px"></div>
				${bars}
				<div class="np-tip" hidden></div>
			</div>
			${parts_axis(data, seconds)}
			<p class="np-text">${esc(chart_reading(data, viewers, seconds, titles))}</p>
		</div>`;
}

// Under the bars: the deck's parts when it marks them, else the first and the last slide.
function parts_axis(data, seconds) {
	const count = seconds.length;
	const parts = data.parts || [];
	if (!parts.length) return `<div class="np-axis"><span>1</span><span>${count}</span></div>`;
	const segments = [];
	let at = 1;
	for (const part of parts) {
		if (part.start > at) segments.push({ start: at, end: part.start - 1, label: "" });
		segments.push({ start: part.start, end: Math.min(part.end, count), label: part.label });
		at = part.end + 1;
	}
	if (at <= count) segments.push({ start: at, end: count, label: "" });
	const sum = (s) => seconds.slice(s.start - 1, s.end).reduce((a, b) => a + b, 0);
	const heaviest = segments.filter((s) => s.label).sort((a, b) => sum(b) - sum(a))[0];
	const columns = segments.map((s) => `${Math.max(1, s.end - s.start + 1)}fr`).join(" ");
	const cells = segments
		.map((s) => {
			const span = s.end > s.start ? `${s.start}–${s.end}` : `${s.start}`;
			const text = s.label ? `${s.label} · ${span}` : "";
			return `<div class="${s === heaviest && sum(s) > 0 ? "np-on" : ""}" title="${esc(text)}">${esc(text)}</div>`;
		})
		.join("");
	return `<div class="np-parts" style="grid-template-columns:${columns}">${cells}</div>`;
}

// One or two sentences, written from the figures only: where they spent the most time, and who stopped where.
function chart_reading(data, viewers, seconds, titles) {
	const out = [];
	const parts = data.parts || [];
	const sum = (p) => seconds.slice(p.start - 1, p.end).reduce((a, b) => a + b, 0);
	const part = parts.length > 1 ? parts.slice().sort((a, b) => sum(b) - sum(a))[0] : null;
	if (part && sum(part) > 0) {
		out.push(__("The part « {0} » holds them the most: {1} on {2} slides.", [part.label, duration(sum(part)), part.end - part.start + 1]));
	} else {
		const best = seconds.indexOf(Math.max(...seconds));
		if (best >= 0 && seconds[best] > 0) {
			out.push(
				titles[best]
					? __("Slide {0}, « {1} », holds them the longest: {2}.", [best + 1, titles[best], duration(seconds[best])])
					: __("Slide {0} holds them the longest: {1}.", [best + 1, duration(seconds[best])])
			);
		}
	}
	const count = seconds.length;
	for (const v of viewers.filter((v) => count && v.slides_seen < count && v.furthest_slide).slice(0, 2)) {
		out.push(__("{0} stops at slide {1}.", [v.who, v.furthest_slide]));
	}
	return out.join(" ");
}

function bind_chart(wrapper, data) {
	const tip = wrapper.find(".np-tip");
	const chart = wrapper.find(".np-chart");
	const titles = data.slide_titles || [];
	const show = function () {
		const slide = Number(this.dataset.slide);
		const title = titles[slide - 1];
		tip.html(`<b>${esc(__("Slide {0}", [slide]))}</b>${title ? esc(title) + "<br>" : ""}${esc(duration(Number(this.dataset.seconds)))}`);
		const box = chart[0].getBoundingClientRect();
		const bar = this.getBoundingClientRect();
		const inner = this.querySelector("i").getBoundingClientRect();
		const x = Math.min(Math.max(bar.left - box.left + bar.width / 2, 90), box.width - 90);
		tip.css({ left: `${x}px`, top: `${inner.top - box.top}px` }).prop("hidden", false);
	};
	const hide = () => tip.prop("hidden", true);
	wrapper.find(".np-bar").on("mouseenter focus", show).on("mouseleave blur", hide);
}

function log_card(data) {
	const device = DEVICE_IN_A_SENTENCE();
	let day = "";
	const items = (data.events || [])
		.map((e) => {
			let text = "";
			const on = device[e.device] || esc(e.device || "");
			if (e.kind === "visit") {
				if (e.new_device) text = __("{0} comes back on {1}: a second device", [esc(e.who), on]);
				else if (e.again) text = __("{0} comes back, on {1}", [esc(e.who), on]);
				else if (e.via === "Copied Link") text = __("{0} enters with the link copied, on {1}", [esc(e.who), on]);
				else text = __("{0} enters, on {1}", [esc(e.who), on]);
			}
			if (e.kind === "video") text = __("{0} watches a video to the end", [esc(e.who)]);
			if (e.kind === "forwarded") text = __("{0} forwards it to {1}", [esc(e.who), esc(e.to)]);
			if (!text) return "";
			const this_day = day_of(e.on);
			const heading = this_day !== day ? `<li class="np-day">${esc(this_day)}</li>` : "";
			day = this_day;
			return `${heading}<li><time>${esc(hour_of(e.on))}</time><span>${text}.</span></li>`;
		})
		.join("");
	return `
		<div class="np-card np-side">
			<h2>${esc(__("What happened"))}</h2>
			<ol class="np-log">${items}</ol>
		</div>`;
}

function people_table(data, viewers, count) {
	const via = { "Link Sent": __("The link sent"), Forwarded: __("Forwarded"), "Copied Link": __("The link copied") };
	const names = DEVICE_NAME();
	const rows = viewers.map((v) => {
		const how = v.forwarded_by ? __("Forwarded by {0}", [v.forwarded_by]) : via[v.entered_via] || "";
		const kinds = (v.device_kinds || []).map((d) => names[d] || d);
		const devices = kinds.length ? kinds.map((d, i) => (i ? d.toLowerCase() : d)).join(", ") : String(v.devices || 1);
		const where = count && v.slides_seen >= count ? pill(__("Saw Everything"), "success") : pill(__("Stops at Slide {0}", [v.furthest_slide || v.slides_seen || 1]), "warn");
		return `<tr>
			<td><div class="np-who">${esc(v.first_name || v.email)}</div>${v.first_name ? `<div class="np-mail">${esc(v.email)}</div>` : ""}</td>
			<td>${esc(how)}</td>
			<td>${esc(devices)}</td>
			<td class="np-num">${esc(duration(v.total_seconds))}</td>
			<td class="np-num">${esc(count ? `${v.slides_seen || 0} / ${count}` : v.slides_seen || 0)}</td>
			<td class="np-num">${v.video_percent ? esc(Math.round(v.video_percent) + " %") : "—"}</td>
			<td class="np-num">${esc(frappe.datetime.prettyDate(v.last_seen_on))}</td>
			<td>${where}</td>
		</tr>`;
	});
	for (const email of data.invited || []) {
		rows.push(`<tr>
			<td><div class="np-who">${esc(email)}</div></td>
			<td>${esc(via["Link Sent"])}</td>
			<td>—</td><td class="np-num">—</td><td class="np-num">—</td><td class="np-num">—</td><td class="np-num">—</td>
			<td>${pill(__("Not Opened Yet"))}</td>
		</tr>`);
	}
	return `
		<div class="np-table-card"><div class="np-scroll">
			<table class="np-table">
				<thead><tr>
					<th>${esc(__("Person"))}</th><th>${esc(__("How They Entered"))}</th><th>${esc(__("Devices"))}</th>
					<th class="np-num">${esc(__("Time"))}</th><th class="np-num">${esc(__("Slides"))}</th><th class="np-num">${esc(__("Video"))}</th>
					<th class="np-num">${esc(__("Last Visit"))}</th><th>${esc(__("Where They Are"))}</th>
				</tr></thead>
				<tbody>${rows.join("")}</tbody>
			</table>
		</div></div>`;
}

// The questions ---------------------------------------------------------------------------------------------------------
function why_forwarded(reason) {
	if (reason === "forward_every_question") return __("The link sends every question to you.");
	if (reason === "no_answerer") return __("Nora is not on this site: the question comes to you.");
	if (reason === "questions_closed") return __("Questions are closed on this link.");
	if (reason === "price_or_commitment") return __("A price or a commitment: Nora leaves it to you.");
	if (reason === "off_topic") return __("Outside the presentation: Nora leaves it to you.");
	if ((reason || "").startsWith("unverified")) return __("Nora's answer did not hold by the slides it cited: she left it to you.");
	return __("Nora did not find a sure answer in the presentation.");
}

function question_where(q) {
	const where = q.slide ? (q.slide_title ? __("on slide {0}, « {1} »", [q.slide, q.slide_title]) : __("on slide {0}", [q.slide])) : "";
	return [where, frappe.datetime.prettyDate(q.asked_on)].filter(Boolean).join(" · ");
}

function render_questions(frm, data) {
	const wrapper = frm.get_field("questions_html").$wrapper;
	const rows = data.questions || [];
	// the head above counts them; here, what they say (Nora's reading, from two questions on), then each one
	const empty = data.mode === NP_MODES.none ? __("Questions are closed on this link.") : __("Nobody has asked a question yet. People ask from the presentation, on the slide on screen.");
	const intro = rows.length ? (rows.length >= 2 ? `<div class="np-reading np-reading-slot"></div>` : "") : `<div class="np-card"><div class="np-empty">${esc(empty)}</div></div>`;
	const waiting = rows.filter((q) => q.status === "Waiting");
	const by_nora = rows.filter((q) => q.status === "Answered by Nora" || q.status === "Asked");
	const answered = rows.filter((q) => q.status === "Answered");
	const card = (q) => `
		<article class="np-waiting" data-name="${esc(q.name)}">
			<div class="np-meta"><span><b>${esc(q.who)}</b> · ${esc(question_where(q))}</span>${pill(__("Waiting for You"), "warn")}</div>
			<div class="np-quote">« ${esc(q.question)} »</div>
			<div class="np-note">${esc(why_forwarded(q.nora_reason))}</div>
			<div>
				<label class="np-field-label" for="np-answer-${esc(q.name)}">${esc(__("Your Answer"))} <span class="np-src">· ${esc(__("sent to {0} by e-mail", [q.email]))}</span></label>
				<textarea class="np-input np-answer" id="np-answer-${esc(q.name)}" rows="4"></textarea>
			</div>
			<div class="np-actions">
				<label class="np-switch"><input type="checkbox" class="np-retained" checked> ${esc(__("Nora keeps this answer for the next people of this link"))}</label>
				<button type="button" class="btn btn-primary btn-sm np-send">${esc(__("Send to {0}", [q.who]))}</button>
			</div>
		</article>`;
	const nora_item = (q) => {
		const done = q.status === "Answered by Nora";
		const sources = done && (q.sources || []).length ? ` <span class="np-src">· ${esc(q.sources.join(", "))}</span>` : "";
		const body = done ? `${esc(q.nora_answer || "")}${sources}` : esc(__("Nora reads the presentation…"));
		const side = done
			? `<span style="display:flex;gap:12px;align-items:center"><button type="button" class="np-link np-correct" data-name="${esc(q.name)}">${esc(__("Correct the answer"))}</button>${pill(__("Answered by Nora"), "success")}</span>`
			: pill(__("Asked"));
		return `
			<div class="np-item">
				<div class="np-meta"><span><b>${esc(q.who)}</b> · ${esc(question_where(q))}</span>${side}</div>
				<div class="np-item-q">« ${esc(q.question)} »</div>
				<div class="np-item-a">${orb()}<div>${body}</div></div>
			</div>`;
	};
	const team_item = (q) => `
		<div class="np-item">
			<div class="np-meta"><span><b>${esc(q.who)}</b> · ${esc(question_where(q))}</span>${pill(__("Answered"), "info")}</div>
			<div class="np-item-q">« ${esc(q.question)} »</div>
			<div class="np-item-a"><div><b>${esc(q.answered_by_name)}</b> ${esc(q.answer || "")}${q.retained ? ` <span class="np-src">· ${esc(__("kept for the next people"))}</span>` : ""}</div></div>
		</div>`;
	const list = (head, items, render) => (items.length ? `<div class="np-list"><div class="np-list-head">${esc(head)}</div>${items.map(render).join("")}</div>` : "");
	wrapper.html(`
		<div class="np-desk">
			${intro}
			${waiting.map(card).join("")}
			${list(__("Answered by Nora"), by_nora, nora_item)}
			${list(__("Answered by the Team"), answered, team_item)}
		</div>`);
	if (rows.length >= 2) {
		frappe.call({ method: "suite.drive.presentation.api.read_questions", args: { name: frm.doc.name }, freeze: false }).then((r) => {
			const text = (r.message || {}).reading;
			if (text) wrapper.find(".np-reading-slot").html(`${orb()}<span>${esc(text)}</span>`);
		});
	}
	wrapper.find(".np-send").on("click", function () {
		const box = $(this).closest(".np-waiting");
		const answer = box.find(".np-answer").val();
		if (!(answer || "").trim()) return frappe.msgprint(__("Write the answer first."));
		reply_question(frm, box.data("name"), answer, box.find(".np-retained").is(":checked") ? 1 : 0, 1);
	});
	wrapper.find(".np-correct").on("click", function () {
		const q = rows.find((row) => row.name === $(this).data("name"));
		correct_answer(frm, q);
	});
}

function reply_question(frm, name, answer, retained, send) {
	frappe
		.call({
			method: "suite.drive.presentation.api.reply_question",
			args: { name, answer, retained, send },
			freeze: true,
		})
		.then(() => {
			frappe.show_alert({ message: send ? __("Your answer is on its way.") : __("Saved."), indicator: "green" });
			frm.reload_doc();
		});
}

function correct_answer(frm, q) {
	const dialog = new frappe.ui.Dialog({
		title: __("Correct Nora's Answer"),
		fields: [
			{ fieldtype: "HTML", options: `<p>« ${esc(q.question)} »</p>` },
			{ fieldname: "answer", fieldtype: "Small Text", label: __("The Right Answer"), reqd: 1, default: q.nora_answer },
			{ fieldname: "send", fieldtype: "Check", label: __("Send it to {0} by e-mail", [q.who]), default: 1 },
			{ fieldname: "retained", fieldtype: "Check", label: __("Nora keeps this answer for the next people of this link"), default: 1 },
		],
		primary_action_label: __("Save"),
		primary_action(values) {
			dialog.hide();
			reply_question(frm, q.name, values.answer, values.retained ? 1 : 0, values.send ? 1 : 0);
		},
	});
	dialog.show();
}

// The sites Nora reads besides the presentation (suite/drive/presentation/sources.py): one address per line, each with
// the pages read and when.
function sites_block(frm, data) {
	const rows = (data.sites || [])
		.map((site) => {
			const state = site.read_on ? __("{0} pages, read {1}", [site.pages, frappe.datetime.prettyDate(site.read_on)]) : __("Being read…");
			return `<li><span>${esc(site.url.replace(/^https?:\/\//, ""))}</span><span class="np-src">${esc(state)}</span></li>`;
		})
		.join("");
	return `
		${rows ? `<ul class="np-sites">${rows}</ul>` : ""}
		<textarea class="np-input np-sites-input" rows="3" aria-label="${esc(__("The websites"))}" placeholder="https://neoffice.ch&#10;https://wiki.neoffice.ch/wiki/manuel">${esc(frm.doc.nora_sites || "")}</textarea>
		<div class="np-sites-actions">
			<button type="button" class="btn btn-default btn-xs np-sites-save">${esc(__("Save"))}</button>
			${rows ? `<button type="button" class="np-link np-sites-read">${esc(__("Read them again now"))}</button>` : ""}
		</div>`;
}

// What Nora knows for this link, and a trial as a visitor ----------------------------------------------------------------
function render_sources(frm, data) {
	const wrapper = frm.get_field("nora_sources_html").$wrapper;
	const mode = frm.doc.questions_mode || NP_MODES.nora;
	const source = (title, state, detail, toggle, action) => `
		<div class="np-source">
			<label class="np-switch" aria-label="${esc(title)}">${toggle}</label>
			<div class="np-source-body">
				<div class="np-source-title">${esc(title)}<span>${esc(state)}</span></div>
				<div class="np-source-detail">${esc(detail)}</div>
				${action || ""}
			</div>
		</div>`;
	const choice = (value, title, detail) => `
		<label class="np-choice"><input type="radio" name="np-mode-${esc(frm.doc.name)}" value="${esc(value)}"${mode === value ? " checked" : ""}>
			<span><b>${esc(title)}</b>${detail ? ` <span>${esc(detail)}</span>` : ""}</span></label>`;
	const lock = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"></rect><path d="M8 11V8a4 4 0 0 1 8 0v3"></path></svg>`;
	wrapper.html(`
		<div class="np-desk">
			<div class="np-row">
				<div class="np-wide" style="display:flex;flex-direction:column;gap:18px;min-width:0">
					<div>
						<p class="np-text" style="font-size:15px">${esc(__("She answers the people who watch the presentation from these sources, and nothing else. What she says always cites where she has it from."))}</p>
						${data.nora ? "" : `<p class="np-warning" style="margin-top:8px">${esc(__("Nora is not on this site: every question goes to the person who answers."))}</p>`}
					</div>
					<div class="np-sources">
						${source(__("The presentation"), __("{0} slides", [data.slides || 0]), __("The text of each slide, and its images' descriptions. Always."), `<input type="checkbox" checked disabled>`)}
						${source(
							__("The speaker notes"),
							frm.doc.nora_reads_notes ? __("Read") : __("Not read"),
							__("They often say what is not said to the client: your choice."),
							`<input type="checkbox" class="np-notes"${frm.doc.nora_reads_notes ? " checked" : ""}>`
						)}
						${source(
							__("Your answers"),
							__("{0} kept", [data.kept || 0]),
							__("What you answered on this link and kept for the next people. Never lent to another link."),
							`<input type="checkbox" checked disabled>`,
							data.kept ? `<button type="button" class="np-link np-see-answers" style="align-self:flex-start;margin-top:2px">${esc(__("See them"))}</button>` : ""
						)}
						${source(
							__("The websites"),
							(data.sites || []).length ? __("{0} sites", [data.sites.length]) : __("None"),
							__("The website and the public manual: Nora takes the pages that speak of the question and cites them. Pages of prices are never read."),
							`<input type="checkbox"${(data.sites || []).length ? " checked" : ""} disabled>`,
							sites_block(frm, data)
						)}
					</div>
					<div class="np-lock">${lock}<div><b>${esc(__("Never, for a person outside:"))}</b> ${esc(__("your clients and their figures, your e-mails, your ERP documents, what Nora learnt about your company. Here Nora has no tool: she reads the sources above, nothing else. A figure she writes must be written in a slide she cites, or she passes the question on."))}</div></div>
					<div class="np-card" style="gap:12px">
						<div style="font-size:15.5px;font-weight:700">${esc(__("When Someone Asks a Question"))}</div>
						${choice(NP_MODES.nora, __("Nora answers, else she forwards to you."), __("You receive the question by e-mail; your answer leaves by e-mail."))}
						${choice(NP_MODES.forward, __("Every question is forwarded to you."), __("Without Nora: the person knows you will answer by e-mail."))}
						${choice(NP_MODES.none, __("No questions on this link."), "")}
						<div class="np-note">${esc(__("The questions go to {0}.", [data.answered_by || ""]))} <button type="button" class="np-link np-who-answers">${esc(__("Change"))}</button></div>
					</div>
				</div>
				<aside class="np-try np-side">
					<div class="np-try-head">${orb()}<h3>${esc(__("Try as a Visitor"))}</h3></div>
					<p class="np-text">${esc(__("Ask the question a client would ask: Nora answers as she would answer them, from these sources."))}</p>
					<div class="np-try-form">
						<textarea class="np-input" rows="2" maxlength="500" aria-label="${esc(__("A question"))}" placeholder="${esc(__("Do our data stay in Switzerland?"))}"></textarea>
						<button type="button" class="btn btn-primary btn-sm np-try-ask">${esc(__("Ask"))}</button>
					</div>
					<div class="np-try-answer" hidden></div>
					<div class="np-try-foot">${esc(__("Nothing is recorded or sent: it is a trial."))}</div>
				</aside>
			</div>
		</div>`);
	wrapper.find(".np-notes").on("change", function () {
		frm.set_value("nora_reads_notes", this.checked ? 1 : 0).then(() => frm.save());
	});
	wrapper.find(`input[name="np-mode-${frm.doc.name}"]`).on("change", function () {
		frm.set_value("questions_mode", this.value).then(() => frm.save());
	});
	wrapper.find(".np-see-answers").on("click", () => open_tab(frm, "questions_tab"));
	wrapper.find(".np-sites-save").on("click", () => {
		frm.set_value("nora_sites", wrapper.find(".np-sites-input").val()).then(() => frm.save());
	});
	wrapper.find(".np-sites-read").on("click", () =>
		frappe.call({ method: "suite.drive.presentation.api.read_sites", args: { name: frm.doc.name } }).then(() =>
			frappe.show_alert({ message: __("Nora reads the sites again: a few minutes."), indicator: "blue" })
		)
	);
	wrapper.find(".np-who-answers").on("click", () => {
		open_tab(frm, "settings_tab");
		frm.scroll_to_field("questions_to");
	});
	// a block, not a <form>: the desk's layout already sits in one, and the browser drops a form inside a form
	const try_it = () => {
		const box = wrapper.find(".np-try-form");
		const input = box.find("textarea");
		const button = box.find("button");
		const out = wrapper.find(".np-try-answer");
		const question = (input.val() || "").trim();
		if (question.length < 3) return;
		button.prop("disabled", true);
		out.prop("hidden", false).html(`${orb()}<div class="np-note">${esc(__("Nora reads the presentation…"))}</div>`);
		const call = frappe.call({ method: "suite.drive.presentation.api.try_question", args: { name: frm.doc.name, question }, freeze: false });
		call.always(() => button.prop("disabled", false));
		call.fail(() => out.prop("hidden", true));
		call.then((r) => {
			const a = r.message || {};
			if (a.sure) {
				const chips = (a.sources || []).map((s) => `<span class="np-chip">${esc(s)}</span>`).join("");
				out.html(`${orb()}<div><div style="white-space:pre-line">${esc(a.answer)}</div><div class="np-chips">${chips}</div></div>`);
			} else {
				out.html(`${orb()}<div><b>${esc(__("Nora would forward this question to {0}.", [data.answered_by || ""]))}</b><div class="np-note">${esc(why_forwarded(a.reason))}</div></div>`);
			}
		});
	};
	wrapper.find(".np-try-ask").on("click", try_it);
	wrapper.find(".np-try-form textarea").on("keydown", (event) => {
		if (event.key === "Enter" && !event.shiftKey) {
			event.preventDefault();
			try_it();
		}
	});
}

// //// Neoffice — added file (no upstream equivalent): the staff's side of a shared presentation: copy or send the link,
// //// withdraw it, and see what each person saw (suite/drive/presentation/api.py get_stats); answer the questions asked
// //// on it and see what Nora knows for it (maintenance#2337).
frappe.ui.form.on("Presentation Link", {
	refresh(frm) {
		frm.get_field("stats_html").$wrapper.empty();
		frm.get_field("questions_html").$wrapper.empty();
		frm.get_field("nora_sources_html").$wrapper.empty();
		if (frm.is_new()) return;
		if (frm.doc.status !== "Withdrawn") {
			frm.add_custom_button(__("Send the Link"), () => send_link(frm)).addClass("btn-primary");
			frm.add_custom_button(__("Copy the Link"), () => frappe.utils.copy_to_clipboard(frm.doc.url));
			frm.add_custom_button(__("Open as a Visitor"), () => window.open(frm.doc.url, "_blank", "noopener"));
			frm.add_custom_button(
				__("Withdraw"),
				() =>
					frappe.confirm(__("The link will open nothing any more. The visits stay."), () =>
						frm.set_value("status", "Withdrawn").then(() => frm.save())
					),
				__("More")
			);
		}
		frappe
			.call("suite.drive.presentation.api.get_stats", { name: frm.doc.name })
			.then((r) => render_stats(frm, r.message || {}));
		frappe.call("suite.drive.presentation.api.get_questions", { name: frm.doc.name }).then((r) => {
			render_questions(frm, r.message || {});
			render_sources(frm, r.message || {});
		});
	},
});

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

function minutes(seconds) {
	seconds = Math.round(seconds || 0);
	if (seconds < 60) return __("{0} s", [seconds]);
	return __("{0} min", [Math.round(seconds / 60)]);
}

function render_stats(frm, data) {
	const esc = frappe.utils.escape_html;
	const viewers = data.viewers || [];
	const wrapper = frm.get_field("stats_html").$wrapper;
	if (!viewers.length) {
		const invited = (data.invited || []).length ? ` ${__("Received, not opened yet: {0}", [data.invited.join(", ")])}` : "";
		wrapper.html(`<p class="text-muted">${esc(__("Nobody has entered yet.") + invited)}</p>`);
		return;
	}
	const count = data.slide_count || 0;
	const per = data.per_slide || {};
	const top = Math.max(1, ...Object.values(per));
	const bars = Array.from({ length: count }, (_, i) => {
		const seconds = per[String(i + 1)] || 0;
		const height = Math.round((seconds / top) * 150);
		const title = __("Slide {0}: {1}", [i + 1, minutes(seconds)]);
		return `<div title="${esc(title)}" style="flex:1 1 0;height:${height}px;min-height:2px;border-radius:4px 4px 0 0;background:#f55d1a"></div>`;
	}).join("");
	const via = { "Link Sent": __("The link sent"), Forwarded: __("Forwarded"), "Copied Link": __("The link copied") };
	const rows = viewers
		.map((v) => {
			const who = v.first_name ? `${esc(v.first_name)} <span class="text-muted">${esc(v.email)}</span>` : esc(v.email);
			const how = v.forwarded_by ? __("Forwarded by {0}", [esc(v.forwarded_by)]) : esc(via[v.entered_via] || "");
			const seen = count ? `${v.slides_seen || 0} / ${count}` : `${v.slides_seen || 0}`;
			return `<tr><td>${who}</td><td>${how}</td><td>${esc(String(v.devices || 1))}</td><td class="text-right">${minutes(v.total_seconds)}</td><td class="text-right">${seen}</td><td class="text-right">${v.video_percent ? v.video_percent + " %" : "–"}</td><td>${esc(frappe.datetime.prettyDate(v.last_seen_on))}</td></tr>`;
		})
		.join("");
	const device = { Computer: __("a computer"), Phone: __("a phone"), Tablet: __("a tablet") };
	const events = (data.events || [])
		.slice()
		.reverse()
		.map((e) => {
			let text = "";
			if (e.kind === "visit") text = __("{0} enters, on {1}", [esc(e.who), device[e.device] || esc(e.device || "")]);
			if (e.kind === "video") text = __("{0} watches a video to the end", [esc(e.who)]);
			if (e.kind === "forwarded") text = __("{0} forwards it to {1}", [esc(e.who), esc(e.to)]);
			return `<li><b>${esc(frappe.datetime.str_to_user(e.on))}</b> ${text}</li>`;
		})
		.join("");
	wrapper.html(`
		<div style="display:flex;gap:32px;flex-wrap:wrap;margin-bottom:18px">
			<div><div style="font-size:32px">${viewers.length}</div><div class="text-muted small">${esc(__("People"))}</div></div>
			<div><div style="font-size:32px">${minutes(data.total_seconds)}</div><div class="text-muted small">${esc(__("Time Watched"))}</div></div>
		</div>
		${count ? `<div class="text-muted small" style="margin-bottom:6px">${esc(__("Time spent on each slide, everyone together"))}</div>
		<div style="display:flex;align-items:flex-end;gap:3px;height:160px;border-bottom:1px solid #d9d2c7;margin-bottom:18px">${bars}</div>` : ""}
		<table class="table table-bordered small">
			<thead><tr><th>${esc(__("Person"))}</th><th>${esc(__("How They Entered"))}</th><th>${esc(__("Devices"))}</th><th class="text-right">${esc(__("Time"))}</th><th class="text-right">${esc(__("Slides"))}</th><th class="text-right">${esc(__("Video"))}</th><th>${esc(__("Last Seen"))}</th></tr></thead>
			<tbody>${rows}</tbody>
		</table>
		${(data.invited || []).length ? `<p class="small">${esc(__("Received, not opened yet: {0}", [data.invited.join(", ")]))}</p>` : ""}
		<div class="text-muted small" style="margin:12px 0 6px">${esc(__("What happened"))}</div>
		<ul class="small" style="padding-left:18px">${events}</ul>
	`);
}

// The questions ---------------------------------------------------------------------------------------------------------
function why_forwarded(reason) {
	if (reason === "forward_every_question") return __("The link sends every question to you.");
	if (reason === "no_answerer") return __("Nora is not on this site: the question comes to you.");
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
	const esc = frappe.utils.escape_html;
	const wrapper = frm.get_field("questions_html").$wrapper;
	const rows = data.questions || [];
	if (!rows.length) {
		const text =
			data.mode === "No Questions"
				? __("Questions are closed on this link.")
				: __("Nobody has asked a question yet. People ask from the presentation, on the slide on screen.");
		wrapper.html(`<p class="text-muted">${esc(text)}</p>`);
		return;
	}
	const number = (value, label) =>
		`<div style="text-align:right"><div style="font-size:34px;line-height:1">${value}</div><div class="text-muted small" style="text-transform:uppercase;letter-spacing:.08em">${esc(label)}</div></div>`;
	const waiting = rows.filter((q) => q.status === "Waiting");
	const others = rows.filter((q) => q.status !== "Waiting");
	const card = (q) => `
		<div class="np-question" data-name="${esc(q.name)}" style="border:1px solid #141414;border-radius:14px;padding:16px 18px;margin-bottom:14px">
			<div class="small" style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap"><span><b>${esc(q.who)}</b> · ${esc(question_where(q))}</span><span class="indicator-pill orange">${esc(__("Waiting for You"))}</span></div>
			<div style="font-size:19px;margin:10px 0 6px;white-space:pre-line">« ${esc(q.question)} »</div>
			<div class="text-muted small" style="margin-bottom:10px">${esc(why_forwarded(q.nora_reason))}</div>
			<textarea class="form-control np-answer" rows="4" placeholder="${esc(__("Your answer, sent to {0} by e-mail", [q.email]))}"></textarea>
			<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:10px">
				<label class="small" style="display:flex;gap:8px;align-items:center;margin:0"><input type="checkbox" class="np-retained" checked> ${esc(__("Nora keeps this answer for the next people of this link"))}</label>
				<button class="btn btn-primary btn-sm np-send">${esc(__("Send to {0}", [q.who]))}</button>
			</div>
		</div>`;
	const line = (q) => {
		let body = "";
		if (q.status === "Answered by Nora") {
			const sources = (q.sources || []).length ? ` <span class="text-muted">· ${esc(q.sources.join(", "))}</span>` : "";
			body = `<div class="small" style="margin-top:4px"><b>${esc(__("Nora"))}</b> ${esc(q.nora_answer || "")}${sources}</div>`;
		} else if (q.status === "Answered") {
			const kept = q.retained ? ` <span class="text-muted">· ${esc(__("kept for the next people"))}</span>` : "";
			body = `<div class="small" style="margin-top:4px;white-space:pre-line"><b>${esc(q.answered_by_name)}</b> ${esc(q.answer || "")}${kept}</div>`;
		} else {
			body = `<div class="small text-muted" style="margin-top:4px">${esc(__("Nora reads the presentation…"))}</div>`;
		}
		const pill =
			q.status === "Answered by Nora"
				? `<span class="indicator-pill green">${esc(__("Answered by Nora"))}</span>`
				: q.status === "Answered"
				? `<span class="indicator-pill blue">${esc(__("Answered"))}</span>`
				: `<span class="indicator-pill gray">${esc(__("Asked"))}</span>`;
		const correct = q.status === "Answered by Nora" ? `<a href="#" class="np-correct small" data-name="${esc(q.name)}">${esc(__("Correct the answer"))}</a>` : "";
		return `
			<div style="border-top:1px solid #f0ebe3;padding:12px 0">
				<div class="small" style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap"><span><b>${esc(q.who)}</b> · ${esc(question_where(q))}</span><span style="display:flex;gap:12px;align-items:center">${correct}${pill}</span></div>
				<div style="font-weight:600;margin-top:6px;white-space:pre-line">« ${esc(q.question)} »</div>
				${body}
			</div>`;
	};
	wrapper.html(`
		<div style="display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:flex-end;margin-bottom:18px">
			<div class="np-reading text-muted" style="max-width:620px"></div>
			<div style="display:flex;gap:28px">${number(data.count, __("Questions"))}${number(data.by_nora, __("Answered by Nora"))}${number(data.waiting, __("Waiting for You"))}</div>
		</div>
		${waiting.map(card).join("")}
		${others.length ? `<div style="margin-top:8px">${others.map(line).join("")}</div>` : ""}
	`);
	if (rows.length >= 2) {
		frappe.call({ method: "suite.drive.presentation.api.read_questions", args: { name: frm.doc.name }, freeze: false }).then((r) => {
			const text = (r.message || {}).reading;
			if (text) wrapper.find(".np-reading").html(`<b>${esc(__("Nora"))}</b> ${esc(text)}`);
		});
	}
	wrapper.find(".np-send").on("click", function () {
		const box = $(this).closest(".np-question");
		const answer = box.find(".np-answer").val();
		if (!(answer || "").trim()) return frappe.msgprint(__("Write the answer first."));
		reply_question(frm, box.data("name"), answer, box.find(".np-retained").is(":checked") ? 1 : 0, 1);
	});
	wrapper.find(".np-correct").on("click", function (event) {
		event.preventDefault();
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
			{ fieldtype: "HTML", options: `<p>« ${frappe.utils.escape_html(q.question)} »</p>` },
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

// What Nora knows for this link ------------------------------------------------------------------------------------------
function render_sources(frm, data) {
	const esc = frappe.utils.escape_html;
	const row = (title, state, detail) =>
		`<div style="border-top:1px solid #f0ebe3;padding:12px 0"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap"><b>${esc(title)}</b><span class="text-muted small">${esc(state)}</span></div><div class="small text-muted" style="margin-top:4px">${esc(detail)}</div></div>`;
	const nora = data.nora
		? ""
		: `<p class="small" style="color:#aa3700">${esc(__("Nora is not on this site: every question goes to the person who answers."))}</p>`;
	frm.get_field("nora_sources_html").$wrapper.html(`
		${nora}
		${row(__("The presentation"), __("{0} slides", [data.slides || 0]), __("The text of each slide, and its images' descriptions. Always."))}
		${row(__("The speaker notes"), frm.doc.nora_reads_notes ? __("Read") : __("Not read"), __("Only when ticked here."))}
		${row(__("Your answers"), __("{0} kept", [data.kept || 0]), __("What you answered on this link and kept for the next people. Never lent to another link."))}
		<div style="background:#f4f2ee;border-radius:12px;padding:12px 14px;margin-top:12px" class="small">
			<b>${esc(__("Never, for a person outside:"))}</b> ${esc(__("your clients and their figures, your e-mails, your ERP documents, what Nora learnt about your company. Here Nora has no tool: she reads the sources above, nothing else. A figure she writes must be written in a slide she cites, or she passes the question on."))}
		</div>
	`);
}

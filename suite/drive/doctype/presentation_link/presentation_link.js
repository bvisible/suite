// //// Neoffice — added file (no upstream equivalent): the staff's side of a shared presentation: copy or send the link,
// //// withdraw it, and see what each person saw (suite/drive/presentation/api.py get_stats).
frappe.ui.form.on("Presentation Link", {
	refresh(frm) {
		frm.get_field("stats_html").$wrapper.empty();
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

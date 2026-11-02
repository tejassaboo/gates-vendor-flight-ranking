// How this plugin's page draws its task's output: the travel desk's decision as a boarding pass, with the
// selected flight, the allowed cabin and the hotel on the pass and the full ranking on its stub. Built only
// from ./kit/components.js; the styles are in renderers.css and use the kit's CSS variables.
import { h, humanize, statusPill } from "./kit/components.js";

function field(label, value) {
  return h("div", { class: "pass-field" }, h("span", { class: "pass-label", text: label }), h("strong", { class: "pass-value", text: value }));
}

function boardingPass(booking, { verdict }) {
  const ranked = booking.ranked_itinerary_ids;
  const pill = verdict.valid ? statusPill("Policy checked", "ok", { icon: true }) : statusPill("Check failed", "bad", { icon: true });
  return h(
    "article",
    { class: "pass" },
    h("header", { class: "pass-head" }, h("span", { class: "pass-brand", text: "Foundation travel desk" }), pill),
    h(
      "div",
      { class: "pass-main" },
      field("Flight", booking.selected_itinerary_id),
      field("Allowed cabin", humanize(booking.allowed_cabin)),
      field("Hotel", booking.hotel_id),
    ),
    h(
      "div",
      { class: "pass-stub" },
      h("span", { class: "pass-label", text: `Ranking, ${ranked.length} itineraries` }),
      h("ol", { class: "pass-rank" }, ranked.map((id, index) => h("li", { class: index === 0 ? "first" : null, text: id }))),
    ),
  );
}

export default { GatesBookingOutput: boardingPass };

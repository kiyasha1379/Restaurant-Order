/**
 * Reservation page: keeps the start times and the floor plan in step with /api/availability.
 *
 * The server draws the first view and validates the booking again when the form is sent,
 * so this script only has to refresh what changes when the day, the number of guests or the
 * time changes. Times and tables are radio buttons: the form works with them natively.
 */
import { setDateField } from "./date-picker.js";
import { JalaliCalendar } from "./jalali-calendar.js";
import { config, fillText, requestJson } from "./site-config.js";

const language = config.language || "fa";

function text(key, values = {}) {
  return fillText(config.texts[key] || "", values);
}

function guestsText(count) {
  const key = count === 1 ? "reserve.guests_unit_one" : "reserve.guests_unit";
  return text(key, { count: JalaliCalendar.localizeDigits(count, language) });
}

export function startReserve() {
  const page = document.querySelector("[data-reserve]");
  if (!page) {
    return;
  }
  const form = page.querySelector("[data-reserve-form]");
  const dateInput = form.querySelector("[data-reserve-date]");
  const guestsInput = form.querySelector("[data-reserve-guests]");
  const guestsLabel = form.querySelector("[data-guests-text]");
  const dateField = form.querySelector("[data-date-field]");
  const dayButtons = [...form.querySelectorAll("[data-day]")];
  const slotsBox = form.querySelector("[data-reserve-slots]");
  const slotsEmpty = form.querySelector("[data-reserve-slots-empty]");
  const planHint = form.querySelector("[data-plan-hint]");
  const planTables = [...form.querySelectorAll("[data-plan-table]")];
  const submit = form.querySelector("[data-reserve-submit]");
  const errorBox = form.querySelector("[data-reserve-error]");
  const summary = {
    day: form.querySelector("[data-sum-day]"),
    time: form.querySelector("[data-sum-time]"),
    guests: form.querySelector("[data-sum-guests]"),
    table: form.querySelector("[data-sum-table]"),
  };
  const maxGuests = Number(page.dataset.maxGuests) || 1;
  let latestRequest = 0;

  const checkedTime = () => slotsBox.querySelector("input:checked");
  const checkedTable = () => form.querySelector("[data-plan-table] input:checked");

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  }

  function digits(value) {
    return JalaliCalendar.localizeDigits(value, language);
  }

  function updateSummary() {
    const day = JalaliCalendar.fromIso(dateInput.value);
    summary.day.textContent = day ? JalaliCalendar.formatFull(day, language) : "";
    const time = checkedTime();
    summary.time.textContent = time ? time.nextElementSibling.textContent : text("reserve.summary.none");
    summary.guests.textContent = guestsText(Number(guestsInput.value));
    const table = checkedTable();
    summary.table.textContent = table
      ? text("reserve.table_label", { label: digits(table.closest("[data-plan-table]").dataset.label) })
      : text("reserve.table_none");
    submit.disabled = !(time && table);
  }

  function renderSlots(data) {
    const previous = checkedTime()?.value;
    const chips = data.slots.map((slot) => {
      const label = document.createElement("label");
      label.className = "time-chip";
      const input = document.createElement("input");
      input.className = "time-chip__input";
      input.type = "radio";
      input.name = "time";
      input.value = slot.time;
      input.disabled = !slot.available;
      input.checked = slot.available && slot.time === previous;
      const face = document.createElement("span");
      face.className = "time-chip__face";
      face.textContent = slot.label;
      label.append(input, face);
      return label;
    });
    slotsBox.replaceChildren(...chips);
    slotsEmpty.hidden = chips.length > 0;
    slotsEmpty.textContent = data.open ? text("reserve.no_slots") : text("reserve.closed_day");
  }

  function renderTables(data) {
    const hasTime = Boolean(checkedTime());
    const states = new Map(data.tables.map((entry) => [entry.id, entry.state]));
    planTables.forEach((card) => {
      const input = card.querySelector("input");
      const state = hasTime ? states.get(Number(input.value)) || "idle" : "idle";
      if (state !== "free") {
        input.checked = false;
      }
      input.disabled = state !== "free";
      card.dataset.state = state;
      const note = state === "busy" ? text("reserve.table.busy") : state === "too_small" ? text("reserve.table.too_small") : "";
      input.setAttribute(
        "aria-label",
        text("reserve.table_aria", {
          label: digits(card.dataset.label),
          seats: text("reserve.seats", { count: digits(card.dataset.capacity) }),
          note,
        }),
      );
    });
    if (planHint) {
      planHint.hidden = hasTime;
    }
  }

  async function refresh() {
    const request = ++latestRequest;
    const params = new URLSearchParams({ date: dateInput.value, guests: guestsInput.value });
    const time = checkedTime()?.value;
    if (time) {
      params.set("time", time);
    }
    try {
      const data = await requestJson(`${config.urls.availability}?${params}`);
      if (request !== latestRequest) {
        return;
      }
      showError("");
      renderSlots(data);
      renderTables(data);
    } catch (error) {
      if (request === latestRequest) {
        showError(error.message || text("reserve.error.generic"));
      }
    }
    updateSummary();
  }

  function chooseDay(iso, fromField) {
    dateInput.value = iso;
    dayButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.day === iso)));
    if (!fromField) {
      setDateField(dateField, "");
    } else {
      dayButtons.forEach((button) => button.setAttribute("aria-pressed", "false"));
    }
    refresh();
  }

  dayButtons.forEach((button) => button.addEventListener("click", () => chooseDay(button.dataset.day, false)));
  dateField.querySelector("[data-date-input]").addEventListener("change", (event) => {
    const picked = event.target.value;
    // A day that is also a quick-day button is shown as that button.
    const quick = dayButtons.find((button) => button.dataset.day === picked);
    if (quick) {
      chooseDay(picked, false);
    } else {
      chooseDay(picked, true);
    }
  });

  form.querySelectorAll("[data-guests-step]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = Math.min(maxGuests, Math.max(1, Number(guestsInput.value) + Number(button.dataset.guestsStep)));
      guestsInput.value = String(next);
      guestsLabel.textContent = guestsText(next);
      refresh();
    });
  });

  slotsBox.addEventListener("change", refresh);
  form.querySelector("[data-reserve-plan]")?.addEventListener("change", updateSummary);
  updateSummary();
}

/**
 * The one Jalali date picker of the site. Customers book a table with it, and the admin panel
 * uses it for manual bookings, special closures and filters. A date is never typed by hand.
 *
 * Markup (see templates/reserve.html):
 *   <div data-date-field data-min="2026-10-26" data-max="2026-11-25" data-closed='["2026-10-30"]'>
 *     <input type="hidden" data-date-input>            holds the chosen day as YYYY-MM-DD
 *     <button type="button" data-date-trigger><span data-date-label></span></button>
 *     <div data-date-panel hidden></div>
 *   </div>
 * The input fires a bubbling `change` event when a day is picked. Send a `datefield:set`
 * event with the day (or "" to clear) to change the field from outside.
 */
import { JalaliCalendar } from "./jalali-calendar.js";
import { config, fillText } from "./site-config.js";

const SET_EVENT = "datefield:set";

function text(key) {
  return config.texts[key] || "";
}

function element(tag, className, content) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (content !== undefined) {
    node.textContent = content;
  }
  return node;
}

const ARROW_PATHS = { previous: "M9 6l6 6-6 6", next: "M15 6l-6 6 6 6" };

function arrowIcon(direction) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "18");
  svg.setAttribute("height", "18");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", ARROW_PATHS[direction]);
  svg.append(path);
  return svg;
}

/**
 * Draws one month into `panel`. In a right-to-left page the "previous" arrow points right,
 * which is what the ARROW_PATHS above draw for `dir="rtl"`; for left-to-right pages they flip.
 */
export class DatePicker {
  constructor(panel, options) {
    this.panel = panel;
    this.language = options.language;
    this.min = options.min;
    this.max = options.max;
    this.closed = options.closed;
    this.onPick = options.onPick;
    this.selected = options.selected || null;
    const today = JalaliCalendar.today();
    const shown = this.selected || today;
    this.view = { year: shown.year, month: shown.month };
  }

  setSelected(date) {
    this.selected = date;
    if (date) {
      this.view = { year: date.year, month: date.month };
    }
  }

  render() {
    const month = JalaliCalendar.monthView({
      ...this.view,
      selected: this.selected,
      min: this.min,
      max: this.max,
      isClosed: (date) => this.closed.has(JalaliCalendar.toIso(date)),
      language: this.language,
    });
    const picker = element("div", "dp");
    picker.setAttribute("role", "group");
    picker.setAttribute("aria-label", text("datepicker.choose"));

    const head = element("div", "dp__head");
    head.append(
      this.navButton("previous", month.hasPrevious, text("datepicker.prev"), month.previous),
      Object.assign(element("b", "dp__title", month.title), { ariaLive: "polite" }),
      this.navButton("next", month.hasNext, text("datepicker.next"), month.next),
    );

    const grid = element("div", "dp__grid");
    month.weekdays.forEach((name) => grid.append(element("span", "dp__weekday", name)));
    month.cells.forEach((cell) => grid.append(this.dayCell(cell)));

    const foot = element("div", "dp__foot");
    const current = element("button", "dp__link", text("datepicker.current_month"));
    current.type = "button";
    current.addEventListener("click", () => {
      const today = JalaliCalendar.today();
      this.view = { year: today.year, month: today.month };
      this.render();
    });
    foot.append(element("span", "", text("datepicker.hint")), current);

    picker.append(head, grid, foot);
    this.panel.replaceChildren(picker);
  }

  navButton(direction, isOn, label, target) {
    if (!isOn) {
      const off = element("span", "dp__nav dp__nav--off");
      off.setAttribute("aria-hidden", "true");
      off.append(arrowIcon(direction));
      return off;
    }
    const button = element("button", "dp__nav");
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.append(arrowIcon(direction));
    button.addEventListener("click", () => {
      this.view = target;
      this.render();
      const again = this.panel.querySelector(`.dp__nav[aria-label="${label}"]`);
      (again || this.panel.querySelector(".dp__day:not(.dp__day--off)"))?.focus();
    });
    return button;
  }

  dayCell(cell) {
    if (cell.kind === "blank") {
      return element("span");
    }
    if (cell.isOff) {
      const off = element("span", "dp__day dp__day--off", cell.label);
      off.setAttribute("aria-disabled", "true");
      off.setAttribute("aria-label", fillText(text("datepicker.unavailable"), { date: cell.aria }));
      return off;
    }
    const button = element("button", "dp__day", cell.label);
    button.type = "button";
    button.setAttribute("aria-pressed", String(cell.isSelected));
    button.setAttribute("aria-label", cell.aria);
    if (cell.isFriday) {
      button.classList.add("dp__day--friday");
    }
    if (cell.isToday) {
      button.classList.add("dp__day--today");
    }
    if (cell.isSelected) {
      button.classList.add("dp__day--selected");
    }
    button.addEventListener("click", () => this.onPick(cell.date));
    return button;
  }
}

function readClosedDays(field) {
  try {
    return new Set(JSON.parse(field.dataset.closed || "[]"));
  } catch {
    return new Set();
  }
}

function setUpField(field) {
  const input = field.querySelector("[data-date-input]");
  const trigger = field.querySelector("[data-date-trigger]");
  const label = field.querySelector("[data-date-label]");
  const panel = field.querySelector("[data-date-panel]");
  const emptyLabel = field.dataset.emptyLabel || label.textContent;
  const language = config.language || "fa";
  const picker = new DatePicker(panel, {
    language,
    min: field.dataset.min ? JalaliCalendar.fromIso(field.dataset.min) : null,
    max: field.dataset.max ? JalaliCalendar.fromIso(field.dataset.max) : null,
    closed: readClosedDays(field),
    selected: input.value ? JalaliCalendar.fromIso(input.value) : null,
    onPick: (date) => {
      showValue(JalaliCalendar.toIso(date));
      close();
      input.dispatchEvent(new Event("change", { bubbles: true }));
      trigger.focus();
    },
  });

  function showValue(iso) {
    const date = iso ? JalaliCalendar.fromIso(iso) : null;
    input.value = date ? iso : "";
    label.textContent = date ? JalaliCalendar.formatFull(date, language) : emptyLabel;
    trigger.setAttribute("aria-pressed", String(Boolean(date)));
    picker.setSelected(date);
  }

  function open() {
    picker.render();
    panel.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    panel.querySelector(".dp__day--selected, .dp__day:not(.dp__day--off)")?.focus();
  }

  function close() {
    panel.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  }

  trigger.addEventListener("click", () => (panel.hidden ? open() : close()));
  field.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      close();
      trigger.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!panel.hidden && !field.contains(event.target)) {
      close();
    }
  });
  field.addEventListener(SET_EVENT, (event) => {
    showValue(event.detail || "");
    close();
  });
}

export function startDateFields() {
  document.querySelectorAll("[data-date-field]").forEach(setUpField);
}

/** Change a date field from outside: `setDateField(field, "2026-10-27")`, or "" to clear. */
export function setDateField(field, iso) {
  field.dispatchEvent(new CustomEvent(SET_EVENT, { detail: iso }));
}

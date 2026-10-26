/**
 * The builder page: keeps the choices, draws the picture and the layer list, shows a live price
 * (confirmed by the server) and adds the build to the cart. Without JavaScript the same form
 * still posts to the server, which checks and prices the build.
 */
import { addCustomBuild } from "./cart.js";
import { createPreview } from "./builder-preview.js";
import { config, fillText, formatNumber, requestJson } from "./site-config.js";

const QUOTE_DELAY_MS = 250;
const MIN_QUANTITY = 1;
const MAX_QUANTITY = 20;

function clampQuantity(value) {
  const number = Number.parseInt(value, 10);
  return Number.isNaN(number) ? MIN_QUANTITY : Math.min(MAX_QUANTITY, Math.max(MIN_QUANTITY, number));
}

class BuilderPage {
  constructor(root, data) {
    this.root = root;
    this.data = data;
    this.form = root.querySelector("[data-builder-form]");
    this.inputs = [...this.form.querySelectorAll('input[name^="step-"]')];
    this.quantityInput = this.form.querySelector("[data-qty]");
    this.addButton = this.form.querySelector("[data-add]");
    this.note = this.form.querySelector("[data-note]");
    this.layerSection = this.form.querySelector("[data-layers]");
    this.layerList = this.form.querySelector("[data-layer-list]");
    this.layerEmpty = this.form.querySelector("[data-layers-empty]");
    this.summary = this.form.querySelector("[data-summary]");
    this.options = new Map();
    data.steps.forEach((step) => step.options.forEach((option) => this.options.set(option.id, option)));
    this.layerOrder = [];
    this.focusRequest = null;
    this.quoteTimer = null;
    this.quoteSerial = 0;
    this.serverBlocked = false;
    const container = root.querySelector("[data-preview]");
    this.drawPreview = createPreview(container, data.preview_kind, data.static_base);
  }

  start() {
    this.form.querySelectorAll("[data-qty-step]").forEach((button) => {
      button.hidden = false;
      button.addEventListener("click", () => this.stepQuantity(Number(button.dataset.qtyStep)));
    });
    this.inputs.forEach((input) => input.addEventListener("change", () => this.refresh()));
    this.quantityInput.addEventListener("change", () => this.refresh());
    this.form.addEventListener("submit", (event) => {
      event.preventDefault();
      this.submit();
    });
    if (this.layerSection) {
      this.layerSection.hidden = false;
    }
    this.refresh();
  }

  quantity() {
    return clampQuantity(this.quantityInput.value);
  }

  stepQuantity(delta) {
    this.quantityInput.value = clampQuantity(this.quantity() + delta);
    this.refresh();
  }

  /** The chosen option ids of each step, in the order of the page. */
  chosenByStep() {
    const chosen = new Map(this.data.steps.map((step) => [step.key, []]));
    this.inputs.forEach((input) => {
      if (input.checked) {
        chosen.get(input.name.replace(/^step-/, "")).push(Number(input.value));
      }
    });
    return chosen;
  }

  /** Keep the layers the customer already arranged; new ones go on top. */
  syncLayerOrder(chosen) {
    const wanted = this.data.steps
      .filter((step) => step.is_layered)
      .flatMap((step) => chosen.get(step.key));
    const kept = this.layerOrder.filter((id) => wanted.includes(id));
    wanted.filter((id) => !kept.includes(id)).forEach((id) => kept.unshift(id));
    this.layerOrder = kept;
  }

  /** The ids to send: ordinary options in step order, then the layers in their order. */
  optionIds(chosen) {
    const plain = this.data.steps.filter((step) => !step.is_layered).flatMap((step) => chosen.get(step.key));
    return [...plain, ...this.layerOrder];
  }

  firstMissingStep(chosen) {
    return this.data.steps.find(
      (step) => step.is_required && chosen.get(step.key).length === 0 && step.options.some((option) => option.is_in_stock),
    );
  }

  refresh() {
    this.quantityInput.value = this.quantity();
    const chosen = this.chosenByStep();
    this.syncLayerOrder(chosen);
    this.renderSummary(chosen);
    this.renderLayers(chosen);
    this.renderPreview(chosen);
    const ids = this.optionIds(chosen);
    const unit = ids.reduce((sum, id) => sum + this.options.get(id).price, 0);
    this.showPrice(unit);
    this.serverBlocked = false;
    this.updateAddButton(chosen);
    this.scheduleQuote(ids);
  }

  showPrice(unit) {
    this.root.querySelector("[data-unit-price]").textContent = formatNumber(unit);
    this.root.querySelector("[data-total-price]").textContent = formatNumber(unit * this.quantity());
  }

  updateAddButton(chosen, serverMessage = "") {
    const missing = this.firstMissingStep(chosen);
    const blocked = Boolean(missing) || this.serverBlocked;
    this.addButton.disabled = blocked;
    if (missing) {
      this.note.textContent = fillText(config.texts["builder.missing_step"], { step: missing.title });
    } else {
      this.note.textContent = serverMessage;
    }
  }

  renderSummary(chosen) {
    const rows = this.data.steps
      .filter((step) => step.options.length)
      .map((step) => {
        const term = document.createElement("dt");
        term.textContent = step.title;
        const detail = document.createElement("dd");
        const names = chosen.get(step.key).map((id) => this.options.get(id).name);
        detail.textContent = names.length ? names.join("، ") : config.texts["builder.summary.none"];
        return [term, detail];
      });
    this.summary.replaceChildren(...rows.flat());
  }

  renderPreview(chosen) {
    if (!this.drawPreview) {
      return;
    }
    const byRole = {};
    this.data.steps.forEach((step) => {
      if (step.role && !step.is_layered) {
        byRole[step.role] = chosen.get(step.key).map((id) => this.options.get(id));
      }
    });
    const bread = this.data.steps.find((step) => step.role === "bread");
    if (bread) {
      byRole.bread = chosen.get(bread.key).map((id) => this.options.get(id));
    }
    this.drawPreview({ byRole, layers: this.layerOrder.map((id) => this.options.get(id)) });
  }

  makeSwatch(option) {
    const swatch = document.createElement("span");
    swatch.className = "layer-row__swatch";
    if (option.image_path) {
      const picture = document.createElement("img");
      picture.src = `${this.data.static_base}${option.image_path}`;
      picture.alt = "";
      swatch.append(picture);
    } else {
      swatch.style.background = option.color || "#888888";
    }
    return swatch;
  }

  makeMoveButton(option, delta, disabled) {
    const key = delta < 0 ? "builder.layers.up" : "builder.layers.down";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "layer-row__move";
    button.textContent = delta < 0 ? "↑" : "↓";
    button.setAttribute("aria-label", fillText(config.texts[key], { name: option.name }));
    button.disabled = disabled;
    button.dataset.layerId = option.id;
    button.dataset.delta = delta;
    button.addEventListener("click", () => this.moveLayer(option.id, delta));
    return button;
  }

  makeFixedRow(textKey, option) {
    const row = document.createElement("li");
    row.className = "layer-row layer-row--fixed";
    const label = document.createElement("span");
    label.className = "layer-row__name";
    label.textContent = fillText(config.texts[textKey], { name: option.name });
    const fixed = document.createElement("span");
    fixed.className = "layer-row__fixed";
    fixed.textContent = config.texts["builder.layers.fixed"];
    row.append(this.makeSwatch(option), label, fixed);
    return row;
  }

  renderLayers(chosen) {
    if (!this.layerList) {
      return;
    }
    const breadStep = this.data.steps.find((step) => step.role === "bread");
    const bread = breadStep && chosen.get(breadStep.key).length ? this.options.get(chosen.get(breadStep.key)[0]) : null;
    const rows = [];
    if (bread) {
      rows.push(this.makeFixedRow("builder.layers.top", bread));
    }
    this.layerOrder.forEach((id, index) => {
      const option = this.options.get(id);
      const row = document.createElement("li");
      row.className = "layer-row";
      const label = document.createElement("span");
      label.className = "layer-row__name";
      label.textContent = option.name;
      const moves = document.createElement("span");
      moves.className = "layer-row__moves";
      moves.append(
        this.makeMoveButton(option, -1, index === 0),
        this.makeMoveButton(option, 1, index === this.layerOrder.length - 1),
      );
      row.append(this.makeSwatch(option), label, moves);
      rows.push(row);
    });
    if (bread) {
      rows.push(this.makeFixedRow("builder.layers.bottom", bread));
    }
    this.layerEmpty.hidden = this.layerOrder.length > 0;
    this.layerList.replaceChildren(...rows);
    this.restoreFocus();
  }

  moveLayer(id, delta) {
    const index = this.layerOrder.indexOf(id);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= this.layerOrder.length) {
      return;
    }
    [this.layerOrder[index], this.layerOrder[target]] = [this.layerOrder[target], this.layerOrder[index]];
    this.focusRequest = { id, delta };
    this.refresh();
  }

  /** After a layer moved, keep keyboard focus on the same button (or its twin at the edge). */
  restoreFocus() {
    if (!this.focusRequest) {
      return;
    }
    const { id, delta } = this.focusRequest;
    this.focusRequest = null;
    const wanted = this.layerList.querySelector(`[data-layer-id="${id}"][data-delta="${delta}"]`);
    const fallback = this.layerList.querySelector(`[data-layer-id="${id}"]:not(:disabled)`);
    (wanted && !wanted.disabled ? wanted : fallback)?.focus();
  }

  scheduleQuote(ids) {
    window.clearTimeout(this.quoteTimer);
    this.quoteTimer = window.setTimeout(() => this.askServer(ids), QUOTE_DELAY_MS);
  }

  /** The server's price replaces the preview price; an invalid build blocks the button. */
  async askServer(ids) {
    const serial = (this.quoteSerial += 1);
    const chosen = this.chosenByStep();
    if (this.firstMissingStep(chosen)) {
      return;
    }
    try {
      const url = config.urls.buildQuote.replace("KEY", encodeURIComponent(this.data.key));
      const quote = await requestJson(url, { option_ids: ids, quantity: this.quantity() });
      if (serial === this.quoteSerial) {
        this.showPrice(quote.unit_price);
      }
    } catch (error) {
      if (serial === this.quoteSerial) {
        this.serverBlocked = true;
        this.updateAddButton(chosen, error.message);
      }
    }
  }

  async submit() {
    const chosen = this.chosenByStep();
    if (this.addButton.disabled || this.firstMissingStep(chosen)) {
      return;
    }
    const added = await addCustomBuild(
      { builder: this.data.key, option_ids: this.optionIds(chosen), quantity: this.quantity() },
      this.addButton,
      this.data.name,
    );
    if (added) {
      this.form.querySelector("[data-cart-link]").hidden = false;
    }
  }
}

export function startBuilder() {
  const root = document.querySelector("[data-builder]");
  const dataElement = document.getElementById("builder-data");
  if (!root || !dataElement) {
    return;
  }
  new BuilderPage(root, JSON.parse(dataElement.textContent)).start();
}

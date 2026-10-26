/**
 * The picture next to the builder steps. It is drawn from data only: each option brings a
 * colour, a shape and a size (or a photo), so a new kind of build needs no new code as long
 * as it reuses one of the pictures (pizza, sandwich, drink). `plain` draws nothing.
 */
const SVG_NS = "http://www.w3.org/2000/svg";
const POP_CLASS = "preview-pop";
const PIZZA_RADIUS = 98;
const GOLDEN_ANGLE = 2.39996;
const TOPPING_COUNT = 18;
const MAX_STACK_HEIGHT = 300;

function svg(name, attributes = {}, children = []) {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
  node.append(...children);
  return node;
}

/** Mix a colour (#rrggbb) with white (positive amount) or black (negative amount). */
export function shade(color, amount) {
  const match = /^#([0-9a-f]{6})$/i.exec(color || "");
  if (!match) {
    return color || "#888888";
  }
  const target = amount >= 0 ? 255 : 0;
  const weight = Math.abs(amount);
  const channels = [0, 2, 4].map((offset) => {
    const value = parseInt(match[1].slice(offset, offset + 2), 16);
    return Math.round(value + (target - value) * weight)
      .toString(16)
      .padStart(2, "0");
  });
  return `#${channels.join("")}`;
}

function imageUrl(option, staticBase) {
  return option && option.image_path ? `${staticBase}${option.image_path}` : null;
}

/** Remember which keys were drawn, so only new pieces play the pop animation. */
class Keyed {
  constructor() {
    this.known = new Set();
  }

  /** Mark nodes that were not there before; forget the ones that left. */
  mark(entries) {
    const current = new Set();
    entries.forEach(([key, node]) => {
      current.add(key);
      if (!this.known.has(key)) {
        node.classList.add(POP_CLASS);
      }
    });
    this.known = current;
  }
}

function pickOne(state, role) {
  return (state.byRole[role] || [])[0] || null;
}

// ---- pizza -----------------------------------------------------------------------------

function disc(radius, option, fallback, defs, id, staticBase) {
  const photo = imageUrl(option, staticBase);
  if (photo) {
    const clip = svg("clipPath", { id: `${id}-clip` }, [svg("circle", { cx: 100, cy: 100, r: radius })]);
    defs.append(clip);
    return svg("image", {
      href: photo,
      x: 100 - radius,
      y: 100 - radius,
      width: radius * 2,
      height: radius * 2,
      preserveAspectRatio: "xMidYMid slice",
      "clip-path": `url(#${id}-clip)`,
    });
  }
  const color = (option && option.color) || fallback;
  const gradient = svg("radialGradient", { id: `${id}-fill`, cx: "40%", cy: "35%", r: "75%" }, [
    svg("stop", { offset: 0, "stop-color": shade(color, 0.22) }),
    svg("stop", { offset: 1, "stop-color": color }),
  ]);
  defs.append(gradient);
  return svg("circle", { cx: 100, cy: 100, r: radius, fill: `url(#${id}-fill)` });
}

function toppingNode(option, x, y, diameter, staticBase) {
  const photo = imageUrl(option, staticBase);
  if (photo) {
    return svg("image", { href: photo, x: x - diameter / 2, y: y - diameter / 2, width: diameter, height: diameter });
  }
  const color = option.color || "#B8321F";
  const half = diameter / 2;
  switch (option.shape) {
    case "ring":
      return svg("circle", { cx: x, cy: y, r: Math.max(half - 1.5, 1), fill: "none", stroke: color, "stroke-width": 3 });
    case "square":
      return svg("rect", {
        x: x - half, y: y - half, width: diameter, height: diameter, rx: 2, fill: color,
        stroke: shade(color, -0.25), "stroke-width": 1, transform: `rotate(24 ${x} ${y})`,
      });
    case "pebble":
      return svg("ellipse", {
        cx: x, cy: y, rx: half * 1.1, ry: half * 0.8, fill: color,
        stroke: shade(color, -0.25), "stroke-width": 1, transform: `rotate(-18 ${x} ${y})`,
      });
    default:
      return svg("circle", { cx: x, cy: y, r: half, fill: color, stroke: shade(color, -0.35), "stroke-width": 1.5 });
  }
}

function createPizza(container, staticBase) {
  const keyed = new Keyed();
  const root = svg("svg", { viewBox: "0 0 200 200", class: "preview__svg", "aria-hidden": "true" });
  container.replaceChildren(root);
  return (state) => {
    const defs = svg("defs");
    const crust = pickOne(state, "crust");
    const sauce = pickOne(state, "sauce");
    const cheese = pickOne(state, "cheese");
    const ring = crust && crust.shape === "thin" ? 4 : 8;
    const sauceInset = 4 + ring;
    const cheeseInset = sauceInset + 5;
    const entries = [];
    const nodes = [svg("circle", { cx: 100, cy: 104, r: PIZZA_RADIUS, fill: "rgb(0 0 0 / 35%)" })];
    nodes.push(disc(PIZZA_RADIUS, crust, "#C98B3E", defs, "pv-crust", staticBase));
    if (crust && crust.shape === "stuffed") {
      nodes.push(svg("circle", { cx: 100, cy: 100, r: PIZZA_RADIUS - 5, fill: "none", stroke: shade(crust.color, 0.3), "stroke-width": 3, opacity: 0.8 }));
    }
    if (sauce) {
      nodes.push(disc(PIZZA_RADIUS - 2 * sauceInset, sauce, "#C8391E", defs, "pv-sauce", staticBase));
    }
    if (cheese) {
      nodes.push(disc(PIZZA_RADIUS - 2 * cheeseInset, cheese, "#E2AE48", defs, "pv-cheese", staticBase));
    }
    const toppings = state.byRole.topping || [];
    if (toppings.length) {
      const maxRadius = (50 - cheeseInset - 5) * 2;
      for (let index = 0; index < TOPPING_COUNT; index += 1) {
        const option = toppings[index % toppings.length];
        const angle = index * GOLDEN_ANGLE;
        const radius = maxRadius * (0.18 + 0.82 * Math.sqrt((index + 0.5) / TOPPING_COUNT));
        const node = toppingNode(
          option, 100 + radius * Math.cos(angle), 100 + radius * Math.sin(angle), (option.amount || 8) * 2, staticBase,
        );
        node.classList.add("preview__topping");
        entries.push([`top-${option.id}-${index}`, node]);
        nodes.push(node);
      }
    }
    keyed.mark(entries);
    root.replaceChildren(defs, ...nodes);
  };
}

// ---- sandwich --------------------------------------------------------------------------

const BREAD_TOP_RADIUS = { bag: "999px 999px 22px 22px", bun: "120px 120px 18px 18px", flat: "18px" };
const BREAD_BOTTOM_RADIUS = { bag: "8px 8px 26px 26px", bun: "8px 8px 24px 24px", flat: "18px" };
const MIN_BOTTOM_HEIGHT = 14;
const BOTTOM_SHARE = 0.62;
const LAYER_GAP = 2;

function stackPiece(option, height, radius, widthPercent, staticBase, key) {
  const piece = document.createElement("div");
  piece.className = "stack__piece";
  piece.dataset.key = key;
  piece.style.height = `${height}px`;
  piece.style.width = `${widthPercent}%`;
  piece.style.borderRadius = radius;
  const photo = imageUrl(option, staticBase);
  if (photo) {
    const picture = document.createElement("img");
    picture.src = photo;
    picture.alt = "";
    piece.append(picture);
  } else {
    piece.style.background = option.color || "#D9A35B";
  }
  return piece;
}

function layerGeometry(option) {
  if (option.shape === "sauce") {
    return { height: option.amount || 6, radius: "6px", width: 96 };
  }
  if (option.shape === "wavy") {
    return { height: option.amount || 12, radius: "16px", width: 106 };
  }
  const height = option.amount || 12;
  return { height, radius: height >= 16 ? "8px" : "3px", width: 100 };
}

function createSandwich(container, staticBase) {
  const keyed = new Keyed();
  const stack = document.createElement("div");
  stack.className = "stack";
  container.replaceChildren(stack);
  return (state) => {
    const bread = pickOne(state, "bread");
    const shape = bread ? bread.shape || "flat" : "flat";
    const topHeight = bread ? bread.amount || 34 : 34;
    const bottomHeight = Math.max(MIN_BOTTOM_HEIGHT, Math.round(topHeight * BOTTOM_SHARE));
    const breadOption = bread || { color: "#D9A35B" };
    const entries = [];
    const pieces = [];
    const add = (key, piece) => {
      entries.push([key, piece]);
      pieces.push(piece);
    };
    add("bread-top", stackPiece(breadOption, topHeight, BREAD_TOP_RADIUS[shape] || "18px", 100, staticBase, "bread-top"));
    state.layers.forEach((option) => {
      const geometry = layerGeometry(option);
      add(`layer-${option.id}`, stackPiece(option, geometry.height, geometry.radius, geometry.width, staticBase, `layer-${option.id}`));
    });
    add("bread-bottom", stackPiece(breadOption, bottomHeight, BREAD_BOTTOM_RADIUS[shape] || "18px", 100, staticBase, "bread-bottom"));
    keyed.mark(entries.filter(([key]) => key.startsWith("layer-")));
    const total = pieces.reduce((sum, piece) => sum + parseFloat(piece.style.height), 0) + LAYER_GAP * (pieces.length - 1);
    stack.style.setProperty("--stack-scale", Math.min(1, MAX_STACK_HEIGHT / total).toFixed(3));
    stack.replaceChildren(...pieces);
  };
}

// ---- drink -----------------------------------------------------------------------------

const GLASS_PATH = "M22 22 L138 22 L124 212 Q123 220 115 220 L45 220 Q37 220 36 212 Z";
const GLASS_TOP = 22;
const GLASS_BOTTOM = 220;
const DEFAULT_LEVEL = 70;
const ICE_POSITIONS = [
  [52, 0.12, -14], [92, 0.04, 9], [70, 0.36, -6], [102, 0.5, 18], [50, 0.64, -20], [84, 0.78, 8],
];

function createDrink(container) {
  const keyed = new Keyed();
  const root = svg("svg", { viewBox: "0 0 160 240", class: "preview__svg", "aria-hidden": "true" });
  container.replaceChildren(root);
  return (state) => {
    const base = pickOne(state, "base");
    const flavors = state.byRole.flavor || [];
    const extras = state.byRole.extra || [];
    const level = (pickOne(state, "size") || {}).amount || DEFAULT_LEVEL;
    const baseColor = (base && base.color) || "#E8D96B";
    const bottomColor = flavors[0] ? flavors[0].color : baseColor;
    const topColor = flavors[1] ? flavors[1].color : baseColor;
    const liquidTop = GLASS_BOTTOM - (GLASS_BOTTOM - GLASS_TOP) * (level / 100);
    const defs = svg("defs", {}, [
      svg("clipPath", { id: "pv-glass" }, [svg("path", { d: GLASS_PATH })]),
      svg("linearGradient", { id: "pv-liquid", x1: 0, y1: 1, x2: 0, y2: 0 }, [
        svg("stop", { offset: 0, "stop-color": bottomColor }),
        svg("stop", { offset: 0.55, "stop-color": baseColor }),
        svg("stop", { offset: 1, "stop-color": topColor }),
      ]),
    ]);
    const hasIce = extras.some((option) => option.shape === "ice");
    const entries = [];
    const ice = ICE_POSITIONS.slice(0, hasIce ? 6 : 3).map(([x, share, rotation], index) => {
      const y = liquidTop + 8 + (GLASS_BOTTOM - liquidTop - 40) * share;
      const node = svg("rect", {
        x, y, width: 22, height: 22, rx: 4, fill: "rgb(255 255 255 / 30%)",
        stroke: "rgb(255 255 255 / 55%)", "stroke-width": 1.2, transform: `rotate(${rotation} ${x + 11} ${y + 11})`,
      });
      entries.push([`ice-${index}`, node]);
      return node;
    });
    const cream = extras.find((option) => option.shape === "cream");
    const drizzle = extras.find((option) => option.shape === "other");
    const creamNode = cream
      ? svg("g", { class: "preview__cream" }, [
          svg("ellipse", { cx: 80, cy: liquidTop - 4, rx: 50, ry: 10, fill: cream.color || "#FBF4E4" }),
          svg("ellipse", { cx: 80, cy: liquidTop - 14, rx: 32, ry: 10, fill: shade(cream.color || "#FBF4E4", 0.2) }),
          svg("ellipse", { cx: 80, cy: liquidTop - 24, rx: 16, ry: 8, fill: cream.color || "#FBF4E4" }),
        ])
      : null;
    if (creamNode) {
      entries.push(["cream", creamNode]);
    }
    const drizzleNode = drizzle
      ? svg("path", {
          d: `M40 ${liquidTop + 10} Q60 ${liquidTop + 2} 80 ${liquidTop + 10} T120 ${liquidTop + 10}`,
          fill: "none", stroke: drizzle.color || "#E0A93A", "stroke-width": 4, "stroke-linecap": "round",
        })
      : null;
    if (drizzleNode) {
      entries.push(["drizzle", drizzleNode]);
    }
    keyed.mark(entries);
    root.replaceChildren(
      defs,
      svg("line", { x1: 108, y1: 4, x2: 96, y2: 150, stroke: "#E3A64B", "stroke-width": 5, "stroke-linecap": "round" }),
      svg("g", { "clip-path": "url(#pv-glass)" }, [
        svg("rect", { x: 20, y: liquidTop, width: 120, height: GLASS_BOTTOM - liquidTop, fill: "url(#pv-liquid)", class: "preview__liquid" }),
        ...ice,
        ...(drizzleNode ? [drizzleNode] : []),
        svg("rect", { x: 40, y: GLASS_TOP + 6, width: 8, height: 180, rx: 4, fill: "rgb(255 255 255 / 12%)" }),
      ]),
      ...(creamNode ? [creamNode] : []),
      svg("path", { d: GLASS_PATH, fill: "none", stroke: "rgb(243 233 220 / 55%)", "stroke-width": 3 }),
    );
  };
}

const RENDERERS = { pizza: createPizza, sandwich: createSandwich, drink: createDrink };

/**
 * Prepare a picture inside `container`. Returns a function that redraws it from
 * `state = { byRole: {role: [option]}, layers: [option] }`, or null when the kind has no picture.
 */
export function createPreview(container, kind, staticBase) {
  const factory = RENDERERS[kind];
  return factory ? factory(container, staticBase) : null;
}

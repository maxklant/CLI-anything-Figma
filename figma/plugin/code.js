// CLI-Anything Bridge — Figma Plugin Main Thread
// Handles all figma.* API calls, communicates with ui.html via postMessage.

figma.showUI(__html__, { visible: true, width: 280, height: 180 });

// ── color utility ─────────────────────────────────────────────────────────────
function hexToRgb(hex) {
  const h = hex.replace('#', '');
  const hasAlpha = h.length === 8;
  return {
    r: parseInt(h.substring(0, 2), 16) / 255,
    g: parseInt(h.substring(2, 4), 16) / 255,
    b: parseInt(h.substring(4, 6), 16) / 255,
    a: hasAlpha ? parseInt(h.substring(6, 8), 16) / 255 : 1.0,
  };
}

function solidFill(hex) {
  const { r, g, b, a } = hexToRgb(hex);
  return [{ type: 'SOLID', color: { r, g, b }, opacity: a }];
}

function solidStroke(hex, weight) {
  const { r, g, b, a } = hexToRgb(hex);
  return [{ type: 'SOLID', color: { r, g, b }, opacity: a }];
}

// ── node lookup helper ────────────────────────────────────────────────────────
function getNode(id) {
  const node = figma.getNodeById(id);
  if (!node) throw new Error('Node not found: ' + id);
  return node;
}

// ── command dispatcher ────────────────────────────────────────────────────────
async function dispatch(command, args) {
  switch (command) {

    // ── creation ──────────────────────────────────────────────────────────────

    case 'create_frame': {
      const f = figma.createFrame();
      f.name = args.name || 'Frame';
      f.resize(args.width || 1440, args.height || 900);
      f.x = args.x || 0;
      f.y = args.y || 0;
      if (args.fill) f.fills = solidFill(args.fill);
      if (args.corner_radius != null) f.cornerRadius = args.corner_radius;
      if (args.parent_id) {
        const parent = figma.getNodeById(args.parent_id);
        if (parent && 'appendChild' in parent) parent.appendChild(f);
      }
      figma.currentPage.selection = [f];
      return { node_id: f.id, name: f.name };
    }

    case 'create_text': {
      const family = args.font_family || 'Inter';
      const style = args.bold ? 'Bold' : (args.font_style || 'Regular');
      await figma.loadFontAsync({ family, style });
      const t = figma.createText();
      t.fontName = { family, style };
      t.characters = String(args.content || '');
      t.fontSize = args.font_size || 16;
      if (args.color) t.fills = solidFill(args.color);
      if (args.x != null) t.x = args.x;
      if (args.y != null) t.y = args.y;
      if (args.parent_id) {
        const parent = figma.getNodeById(args.parent_id);
        if (parent && 'appendChild' in parent) parent.appendChild(t);
      }
      return { node_id: t.id, name: t.name };
    }

    case 'create_rect': {
      const r = figma.createRectangle();
      r.name = args.name || 'Rectangle';
      r.resize(args.width || 100, args.height || 100);
      r.x = args.x || 0;
      r.y = args.y || 0;
      if (args.fill) r.fills = solidFill(args.fill);
      if (args.stroke) {
        r.strokes = solidStroke(args.stroke);
        r.strokeWeight = args.stroke_weight || 1;
        r.strokeAlign = 'INSIDE';
      }
      if (args.corner_radius != null) r.cornerRadius = args.corner_radius;
      if (args.parent_id) {
        const parent = figma.getNodeById(args.parent_id);
        if (parent && 'appendChild' in parent) parent.appendChild(r);
      }
      return { node_id: r.id, name: r.name };
    }

    case 'create_ellipse': {
      const e = figma.createEllipse();
      e.name = args.name || 'Ellipse';
      e.resize(args.width || 100, args.height || 100);
      e.x = args.x || 0;
      e.y = args.y || 0;
      if (args.fill) e.fills = solidFill(args.fill);
      if (args.parent_id) {
        const parent = figma.getNodeById(args.parent_id);
        if (parent && 'appendChild' in parent) parent.appendChild(e);
      }
      return { node_id: e.id, name: e.name };
    }

    case 'create_component': {
      const c = figma.createComponent();
      c.name = args.name || 'Component';
      c.resize(args.width || 200, args.height || 200);
      if (args.fill) c.fills = solidFill(args.fill);
      if (args.x != null) c.x = args.x;
      if (args.y != null) c.y = args.y;
      return { node_id: c.id, name: c.name };
    }

    case 'create_instance': {
      const comp = figma.getNodeById(args.component_id);
      if (!comp || comp.type !== 'COMPONENT') throw new Error('Component not found: ' + args.component_id);
      const inst = comp.createInstance();
      if (args.x != null) inst.x = args.x;
      if (args.y != null) inst.y = args.y;
      if (args.parent_id) {
        const parent = figma.getNodeById(args.parent_id);
        if (parent && 'appendChild' in parent) parent.appendChild(inst);
      }
      return { node_id: inst.id, name: inst.name };
    }

    // ── layout ────────────────────────────────────────────────────────────────

    case 'auto_layout': {
      const node = getNode(args.node_id);
      if (!('layoutMode' in node)) throw new Error('Node does not support auto layout');
      const dir = (args.direction || 'horizontal').toUpperCase();
      node.layoutMode = dir === 'VERTICAL' ? 'VERTICAL' : 'HORIZONTAL';
      node.primaryAxisSizingMode = 'AUTO';
      node.counterAxisSizingMode = 'AUTO';
      if (args.gap != null) node.itemSpacing = args.gap;
      if (args.padding != null) {
        node.paddingTop = args.padding;
        node.paddingBottom = args.padding;
        node.paddingLeft = args.padding;
        node.paddingRight = args.padding;
      }
      if (args.padding_h != null) { node.paddingLeft = args.padding_h; node.paddingRight = args.padding_h; }
      if (args.padding_v != null) { node.paddingTop = args.padding_v; node.paddingBottom = args.padding_v; }
      if (args.align) {
        const m = { center: 'CENTER', start: 'MIN', end: 'MAX', 'space-between': 'SPACE_BETWEEN' };
        node.counterAxisAlignItems = m[args.align] || 'MIN';
      }
      if (args.primary_align) {
        const m = { center: 'CENTER', start: 'MIN', end: 'MAX', 'space-between': 'SPACE_BETWEEN' };
        node.primaryAxisAlignItems = m[args.primary_align] || 'MIN';
      }
      return { node_id: node.id };
    }

    // ── mutation ──────────────────────────────────────────────────────────────

    case 'move': {
      const node = getNode(args.node_id);
      if (args.x != null) node.x = args.x;
      if (args.y != null) node.y = args.y;
      return { node_id: node.id, x: node.x, y: node.y };
    }

    case 'resize': {
      const node = getNode(args.node_id);
      if (!('resize' in node)) throw new Error('Node is not resizable');
      node.resize(args.width, args.height);
      return { node_id: node.id, width: node.width, height: node.height };
    }

    case 'delete': {
      const node = getNode(args.node_id);
      const id = node.id;
      node.remove();
      return { deleted: id };
    }

    case 'select': {
      const node = getNode(args.node_id);
      figma.currentPage.selection = [node];
      figma.viewport.scrollAndZoomIntoView([node]);
      return { node_id: node.id, name: node.name };
    }

    case 'fill': {
      const node = getNode(args.node_id);
      if (!('fills' in node)) throw new Error('Node does not support fills');
      node.fills = solidFill(args.color);
      return { node_id: node.id };
    }

    case 'stroke': {
      const node = getNode(args.node_id);
      if (!('strokes' in node)) throw new Error('Node does not support strokes');
      node.strokes = solidStroke(args.color);
      node.strokeWeight = args.weight || 1;
      node.strokeAlign = args.align || 'INSIDE';
      return { node_id: node.id };
    }

    case 'font': {
      const node = getNode(args.node_id);
      if (node.type !== 'TEXT') throw new Error('Node is not a text node');
      const family = args.family || node.fontName.family;
      const style = args.weight || node.fontName.style;
      await figma.loadFontAsync({ family, style });
      node.fontName = { family, style };
      if (args.size != null) node.fontSize = args.size;
      if (args.color) node.fills = solidFill(args.color);
      if (args.line_height != null) node.lineHeight = { value: args.line_height, unit: 'PIXELS' };
      if (args.letter_spacing != null) node.letterSpacing = { value: args.letter_spacing, unit: 'PIXELS' };
      return { node_id: node.id };
    }

    case 'opacity': {
      const node = getNode(args.node_id);
      node.opacity = Math.max(0, Math.min(1, args.value));
      return { node_id: node.id, opacity: node.opacity };
    }

    case 'rename': {
      const node = getNode(args.node_id);
      node.name = args.new_name;
      return { node_id: node.id, name: node.name };
    }

    case 'duplicate': {
      const node = getNode(args.node_id);
      const clone = node.clone();
      if (args.x != null) clone.x = args.x;
      if (args.y != null) clone.y = args.y;
      return { node_id: clone.id, name: clone.name };
    }

    case 'corner_radius': {
      const node = getNode(args.node_id);
      if (!('cornerRadius' in node)) throw new Error('Node does not support corner radius');
      node.cornerRadius = args.radius;
      return { node_id: node.id };
    }

    case 'visible': {
      const node = getNode(args.node_id);
      node.visible = args.visible !== false;
      return { node_id: node.id, visible: node.visible };
    }

    case 'blend_mode': {
      const node = getNode(args.node_id);
      node.blendMode = (args.mode || 'NORMAL').toUpperCase();
      return { node_id: node.id };
    }

    // ── page ──────────────────────────────────────────────────────────────────

    case 'clear_page': {
      const page = figma.currentPage;
      const children = Array.prototype.slice.call(page.children);
      for (var i = 0; i < children.length; i++) children[i].remove();
      return { cleared: true, page: page.name };
    }

    case 'get_selection': {
      const sel = figma.currentPage.selection;
      return { nodes: sel.map(n => ({ id: n.id, name: n.name, type: n.type })) };
    }

    case 'plugin_status': {
      return {
        connected: true,
        page: figma.currentPage.name,
        file: figma.root.name,
        selection_count: figma.currentPage.selection.length,
      };
    }

    default:
      throw new Error('Unknown command: ' + command);
  }
}

// ── message handler ───────────────────────────────────────────────────────────
figma.ui.onmessage = async (msg) => {
  const { id, command, args } = msg;
  if (!command) return;
  try {
    const result = await dispatch(command, args || {});
    figma.ui.postMessage(Object.assign({ id: id, status: 'ok' }, result));
  } catch (e) {
    figma.ui.postMessage({ id, status: 'error', error: e.message });
  }
};

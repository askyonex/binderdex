/* Binderdex: Mehrsprachigkeit im Browser.
 *
 * Die Oberflaeche ist auf Deutsch geschrieben. Dieses Skript laedt das Woerterbuch der gewaehlten Sprache
 * (static/i18n/<lang>.json, ausgeliefert als /i18n/<lang>.js) und uebersetzt alle Texte, die auf der Seite
 * erscheinen: Texte, title-, placeholder- und aria-label-Attribute sowie alert/confirm/prompt.
 *
 * Schluessel = deutscher Originaltext (Leerraum zusammengefasst). Eingefuegte Werte heissen {0}, {1}, ...:
 *   "{0} Karten": "{0} cards"     "{0} liegt im Nebenstapel.": "{0} is in the side pile."
 * Teile, die in einen Platzhalter fallen, werden selbst wieder nachgeschlagen (z. B. "Selten" in "{0} · {1}").
 * Fehlt ein Schluessel, bleibt der deutsche Text stehen. Eine neue Sprache = neue JSON-Datei + Eintrag in NAMES
 * (hier) und UI_LANGS (app.py).
 *
 * Muss im <head> vor allen anderen Skripten stehen (window.BDX_CFG kommt vom Server).
 */
(function () {
  "use strict";
  const SRC = "de";
  const NAMES = {de: "Deutsch", en: "English", es: "Español"};
  const LOCALES = {de: "de-DE", en: "en-GB", es: "es-ES"};
  const cfg = window.BDX_CFG || {langs: ["de"], default: "de", configured: true, v: ""};
  const get = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const ok = l => !!l && cfg.langs.indexOf(l) >= 0;

  function guess() {                       // Erststart: Sprache des Browsers, wenn verfuegbar
    for (const l of navigator.languages || [navigator.language || ""]) {
      const k = String(l).slice(0, 2).toLowerCase();
      if (ok(k)) return k;
    }
    return ok("de") ? "de" : cfg.langs[0];
  }

  let lang = new URLSearchParams(location.search).get("ui");
  if (!ok(lang)) lang = get("uiLang");
  if (!ok(lang)) lang = cfg.configured ? cfg.default : guess();
  if (!ok(lang)) lang = cfg.langs[0] || SRC;
  document.documentElement.lang = lang;
  document.cookie = "ui_lang=" + lang + "; path=/; max-age=31536000; SameSite=Lax";   // Server: Namen, Exporte
  if (lang !== SRC) document.write('<script src="/i18n/' + lang + '.js?v=' + (cfg.v || "") + '"><\/script>');

  /* ---------- Nachschlagen ---------- */
  const LETTER = /[A-Za-zÀ-ÿ]/;
  let D = null, PATS = [];
  const cache = new Map();

  function compile() {
    if (D || !window.BDX_DICT) return !!D;
    D = window.BDX_DICT;
    for (const k in D) {
      if (k.indexOf("{") < 0 || !/\{\d+\}/.test(k)) continue;
      const parts = k.split(/\{(\d+)\}/);
      let re = "^", lit = "";
      for (let i = 0; i < parts.length; i++) {
        if (i % 2) re += "([\\s\\S]*?)";
        else {
          re += parts[i].replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
          if (parts[i].trim().length > lit.length) lit = parts[i].trim();
        }
      }
      const litLen = k.replace(/\{\d+\}/g, "").replace(/\s/g, "").length;
      PATS.push({re: new RegExp(re + "$"), tpl: D[k], lit, litLen, ident: D[k] === k, score: litLen});
    }
    PATS.sort((a, b) => b.score - a.score);
    return true;
  }

  // Bestes Ergebnis = das, bei dem am meisten deutscher Text uebersetzt wurde (Muster koennen mehrdeutig passen)
  function core(c, depth) {
    if (Object.prototype.hasOwnProperty.call(D, c)) return D[c];
    if (cache.has(c)) return cache.get(c);
    let out = null, best = 0;
    if (depth < 3) {
      for (const p of PATS) {
        if (p.lit && c.indexOf(p.lit) < 0) continue;
        const m = p.re.exec(c);
        if (!m) continue;
        let gain = p.ident ? 0 : p.litLen, rest = false;
        const r = p.tpl.replace(/\{(\d+)\}/g, (_, i) => {
          const g = m[+i + 1] == null ? "" : m[+i + 1], x = part(g, depth + 1);
          if (x !== g) gain += g.length; else if (LETTER.test(g)) rest = true;
          return x;
        });
        if (!p.ident && !rest) { out = r; best = Infinity; break; }   // passt vollstaendig: nehmen
        if (gain > best) { best = gain; out = r; }
      }
      if (best !== Infinity && c.indexOf(" · ") > 0) {                 // "Selten · im Binder": Teile einzeln (auch als "· Teil")
        let gain = 0;
        const r = c.split(" · ").map(seg => { const x = part(seg, depth + 1); if (x !== seg) gain += seg.length; return x; }).join(" · ");
        if (gain > best) { best = gain; out = r; }
      }
    }
    if (cache.size > 40000) cache.clear();
    cache.set(c, out);
    return out;
  }

  function core1(seg, depth) { return LETTER.test(seg) ? core(seg.replace(/\s+/g, " ").trim(), depth) : null; }

  function part(g, depth) {                 // eingesetzter Teil eines Musters, notfalls als "· Teil" nachschlagen
    const r = t(g, depth);
    if (r !== g || !LETTER.test(g) || depth >= 3) return r;
    const r2 = core1("· " + g, depth);
    return r2 == null ? g : g.match(/^\s*/)[0] + r2.replace(/^·\s*/, "") + g.match(/\s*$/)[0];
  }

  /** Text uebersetzen (Leerraum am Rand bleibt erhalten). Unbekanntes kommt unveraendert zurueck. */
  function t(s, depth) {
    if (lang === SRC || s == null) return s;
    s = String(s);
    if (!LETTER.test(s) || !compile()) return s;
    const c = s.replace(/\s+/g, " ").trim();
    const out = core(c, depth || 0);
    if (out == null) return s;
    const lead = /^\s*/.exec(s)[0], trail = /\s*$/.exec(s)[0];
    return lead + out + trail;
  }

  /* ---------- Seite uebersetzen ---------- */
  const SKIP = {SCRIPT: 1, STYLE: 1, TEXTAREA: 1, PRE: 1, CODE: 1, NOSCRIPT: 1};
  const ATTRS = ["title", "placeholder", "aria-label"];
  const done = new WeakMap();

  function skipEl(el) {
    for (let e = el; e && e.nodeType === 1; e = e.parentNode) {
      if (SKIP[e.nodeName] || e.isContentEditable || e.getAttribute("translate") === "no" || (e.classList && e.classList.contains("notranslate"))) return true;
      if (e === document.body) break;
    }
    return false;
  }

  function doText(n) {
    const v = n.data;
    if (!v || done.get(n) === v || !LETTER.test(v)) return;
    if (skipEl(n.parentNode)) return;
    const out = t(v);
    done.set(n, out);
    if (out !== v) n.data = out;
  }

  function doAttrs(el) {
    if (skipEl(el.parentNode)) return;    // notranslate gilt fuer den Inhalt, nicht fuer title/placeholder
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (!v || !LETTER.test(v)) continue;
      const key = "a:" + a;
      let m = done.get(el);
      if (m && m[key] === v) continue;
      const out = t(v);
      if (!m) { m = {}; done.set(el, m); }
      m[key] = out;
      if (out !== v) el.setAttribute(a, out);
    }
  }

  function walk(root) {
    if (root.nodeType === 3) return doText(root);
    if (root.nodeType !== 1 && root.nodeType !== 11) return;
    if (root.nodeType === 1) {
      if (SKIP[root.nodeName]) return;
      doAttrs(root);
    }
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = tw.nextNode(); n; n = tw.nextNode()) doText(n);
    if (root.querySelectorAll) for (const el of root.querySelectorAll("[title],[placeholder],[aria-label]")) doAttrs(el);
  }

  if (lang !== SRC) {
    new MutationObserver(muts => {
      if (!compile()) return;
      for (const m of muts) {
        if (m.type === "characterData") doText(m.target);
        else if (m.type === "attributes") doAttrs(m.target);
        else for (const n of m.addedNodes) walk(n);
      }
    }).observe(document.documentElement, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS});

    const A = window.alert.bind(window), C = window.confirm.bind(window), P = window.prompt.bind(window);
    window.alert = m => A(t(m));
    window.confirm = m => C(t(m));
    window.prompt = (m, d) => P(t(m), d);

    const start = () => { compile(); document.title = t(document.title); walk(document.body); };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
  }

  /** Sprache auf diesem Geraet wechseln (neu laden, damit alles in der neuen Sprache erscheint). */
  function setLang(l) {
    try { localStorage.setItem("uiLang", l); } catch (e) {}
    document.cookie = "ui_lang=" + l + "; path=/; max-age=31536000; SameSite=Lax";
    const u = new URL(location.href); u.searchParams.delete("ui");
    location.replace(u.toString());
  }

  window.I18N = {
    lang, src: SRC, names: NAMES, all: Object.keys(NAMES), langs: cfg.langs.slice(), default: cfg.default,
    configured: !!cfg.configured, locale: LOCALES[lang] || "de-DE", t, setLang,
  };
})();

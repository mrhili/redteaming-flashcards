# README.md — Red Team Flashcards

## Introduction

Welcome to **Red Team Flashcards** — a tiny, focused single-page app for memorizing offensive security concepts (conceptual only; intentionally non-actionable). The app reads a `cards.json` file (your JSON "database") and displays randomized flashcards with a front (question + hints) and back (answer + metadata). Users label cards (`difficulty`, `grasped`, `usefulness`) and those labels persist locally (via localForage) or can be saved server-side if you choose the Laravel option.

This README teaches people how to write a correct `cards.json` configuration so the app reads it reliably and without spelling traps.

you can test it live here https://mrhili.github.io/redteaming-flashcards/

---

## Quick start

1. Put a `cards.json` file in the same folder as `index.html`.
2. Serve the folder with a static server (e.g. `python -m http.server 8000`) and open `http://localhost:8000`.
3. Use the Import button to load a combined export file (dataset + labels) or replace `cards.json` and refresh the page.

---

## `cards.json` — structure and rules

The app expects `cards.json` to be a JSON **array** of card objects. Each object must follow the schema and allowed values below. Keep your file well-formed JSON (no trailing commas, proper quoting).

### Minimal card example

```json
{
  "id": "rt-0001",
  "question": "What is spear-phishing?",
  "hints": ["Targets specific users", "May include macro-enabled docs"],
  "answer": "Spear-phishing is a targeted phishing approach...",
  "categories": ["initial-access","phishing"],
  "difficulty": "medium",
  "grasped": false,
  "usefulness": "useful",
  "created_at": "2025-09-08T12:00:00Z",
  "meta": {"review_count": 0}
}
```

### Required & optional fields

* `id` **(required, string)** — unique card identifier. Use a simple pattern like `rt-0001`. Avoid spaces. Recommended regex: `^[a-z0-9\-_.]+$`.
* `question` **(required, string)** — the front text you want to memorize.
* `hints` **(optional, array of strings)** — short hint lines shown on the front.
* `answer` **(required, string)** — the back of the card.
* `categories` **(optional, array of strings)** — taxonomy tags (see allowed examples below).
* `difficulty` **(required, string)** — allowed values: `easy`, `medium`, `hard`. **Spell exactly**. The app uses these exact strings for filtering and keyboard shortcuts.
* `grasped` **(optional, boolean)** — `true` or `false`. The app will update this locally.
* `usefulness` **(optional, string)** — allowed values: `useful`, `dangerous`, `information`. Pick one to help group cards by intent/value.
* `created_at` **(optional, string)** — ISO 8601 date/time (e.g., `2025-09-08T12:00:00Z`) recommended for record-keeping.
* `meta` **(optional, object)** — free-form metadata like `{"review_count":0, "score": 123}`.

> If a field is missing: the app will try to fall back to sensible defaults (e.g., `difficulty: "medium"`), but it's better to include required fields explicitly.

---

## Allowed values and common spelling traps

Spell values exactly. The app performs literal string comparisons.

* **difficulty**: only `easy`, `medium`, `hard`. Mistyped values like `med`, `Medium`, `Hard `, or `mdeium` will not match filters.
* **usefulness**: `useful`, `dangerous`, `information`. Avoid `info`, `danger`, `usefull`.
* **grasped**: boolean **not** string. Use `true` or `false`, not `"true"`.
* **categories**: free-form strings but keep them consistent across cards (e.g., `initial-access`, `privilege-escalation`, `persistence`, `c2`, `exfiltration`, `osint`, `reconnaissance`, `lateral-movement`). Use hyphenation rather than spaces to avoid accidental duplicates (`"privilege escalation"` vs `"privilege-escalation"`).

### Example of a common mistake (bad):

```json
{
  "id": "rt1",
  "question": "...",
  "difficulty": "Medium",
  "grasped": "false"
}
```

* `Medium` has uppercase M: wrong. Use lowercase `medium`.
* `grasped` is a string: wrong. Use boolean `false`.

---

## Full `cards.json` example (array)

```json
[
  {
    "id": "rt-0001",
    "question": "What is spear-phishing?",
    "hints": ["Targets specific users", "May include macro-enabled docs"],
    "answer": "A targeted phishing technique that delivers malicious payloads via socially-engineered messages.",
    "categories": ["initial-access","phishing"],
    "difficulty": "medium",
    "grasped": false,
    "usefulness": "useful",
    "created_at": "2025-09-08T12:00:00Z",
    "meta": {"review_count": 0}
  },
  {
    "id": "rt-0002",
    "question": "What is OSINT?",
    "hints": ["Open sources", "Publicly available"],
    "answer": "Open-source intelligence: passive recon from public sources.",
    "categories": ["reconnaissance","osint"],
    "difficulty": "easy",
    "grasped": false,
    "usefulness": "information",
    "created_at": "2025-09-08T12:15:00Z",
    "meta": {"review_count": 0}
  }
]
```

---

## JSON validation helper (small JS snippet)

Drop this into the browser console or a Node script to sanity-check your `cards.json` before using it. It performs fast, clear checks and reports where things go wrong.

```javascript
// validation.js — simple validator (no external deps)
function validateCards(cards){
  const allowedDiff = ['easy','medium','hard'];
  const allowedUse = ['useful','dangerous','information'];
  const idRe = /^[a-z0-9\-_.]+$/;
  const errors = [];
  if(!Array.isArray(cards)) return ['Top-level JSON must be an array of cards'];
  cards.forEach((c, i)=>{
    const path = `cards[${i}]`;
    if(!c.id || typeof c.id !== 'string' || !idRe.test(c.id)) errors.push(`${path}.id must be a lowercase string matching ${idRe}`);
    if(!c.question || typeof c.question !== 'string') errors.push(`${path}.question must be a non-empty string`);
    if(!c.answer || typeof c.answer !== 'string') errors.push(`${path}.answer must be a non-empty string`);
    if('difficulty' in c && !allowedDiff.includes(c.difficulty)) errors.push(`${path}.difficulty must be one of: ${allowedDiff.join(', ')}`);
    if('usefulness' in c && !allowedUse.includes(c.usefulness)) errors.push(`${path}.usefulness must be one of: ${allowedUse.join(', ')}`);
    if('grasped' in c && typeof c.grasped !== 'boolean') errors.push(`${path}.grasped must be boolean (true/false)`);
    if('hints' in c && !Array.isArray(c.hints)) errors.push(`${path}.hints must be an array of strings`);
    if('categories' in c && !Array.isArray(c.categories)) errors.push(`${path}.categories must be an array of strings`);
  });
  return errors;
}

// Usage in browser console:
// fetch('cards.json').then(r=>r.json()).then(cards=>{ const errs=validateCards(cards); console.log(errs.length?errs:'OK') })
```

This validator is intentionally minimal (no AJV) but will catch the common mistakes described earlier.

---

## Import / Export behavior

* **Export:** creates a file `flashcards-export.json` containing two keys: `dataset` (cards array) and `labels` (your local edits). You can re-import this file to restore both.
* **Import:** accepts either a raw cards array (replaces the dataset) or the export format `{ dataset, labels }` (replaces dataset and restores labels).

Tips:

* If you want to keep your original `cards.json` untouched while you edit, use Export to make backups before changing data.
* If using the static version, edits to `cards.json` on disk will be reflected after page refresh.

---

## Storage & server notes

* **Static/local-first mode:** the app fetches `cards.json` and stores per-card user labels locally in browser storage (localForage). This is simplest and requires no server.
* **Laravel option (optional):** if you want centralized persistence, the app can talk to a Laravel API (e.g., `GET /api/cards`, `PATCH /api/cards/{id}`). The server can keep a `cards.json` in storage and apply changes when `PATCH` updates labels. The client code uses the same data shape.

If you request the Laravel scaffolding I can provide the routes/controllers that read/write `storage/app/cards.json` and return JSON.

---

## UI cheat sheet (keyboard & controls)

* Flip card: click card or press `F`.
* Next / Prev: buttons or `N` / `P` keys.
* Difficulty: click buttons or `1` / `2` / `3` keys (maps to `easy`/`medium`/`hard`).
* Toggle Grasped: `G`.
* Cycle Usefulness: `U`.
* Search & filters: topbar controls.

---

## Contributing and style guide for cards

* Keep answers concise (one paragraph) and non-actionable (focus on concepts, not exploitation steps).
* Use consistent categories and hyphenation to make filters useful.
* Always validate new JSON with the validator before sharing.


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Trimble Connect 3D Viewer side-panel extension ("Merknader") that lets project admins mark elements two ways — add/remove a **vimpel** (flag marker) on a single selected element, or **fargelegge** (color) one or more selected elements with one of 5 standard colors — replacing today's manual workflow of running a local Flask app (`D:\SOS-Kolbotn\app`) and uploading the result by hand. See [README.md](README.md) for user-facing status and the role-gating explanation.

This is a **separate project/repo** from `D:\Trimble connect` ("Søk Armering") — each Trimble Connect extension Kåre builds gets its own repo, its own GitHub Pages URL, and its own manifest.json, even though the frontend skeleton is copied from that project.

## Current status: Nivå 1 (queue export, no server/OAuth) — done and verified live in a real Trimble Connect project (2026-07-06)

Three ambition levels were scoped out for how the frontend hands off to the ifcopenshell edit (see "Why Nivå 1" below). **Nivå 1 is what's built and current:**

**Frontend (`app.js`):** connects to Trimble Connect, reads the current user's role from the project's own member list, gates the UI to admins, and supports **two marker types** sharing the same selection/queue infrastructure:
- **Vimpel** (`add-btn`/`remove-btn`) — requires exactly one selected element.
- **Fargelegging** (`fargeButtons`, one of 5 preset colors) — works with one or more selected elements; confirming a color adds one queue item per selected element (see `submitFargeForm()`).

Both build a queue-item-shaped payload and call `addToQueue()` — instead of calling any backend automatically, items are **appended to an in-page queue list**, and the user downloads the whole queue as a `.json` file (`downloadQueue()`). No network call happens at all.

**Backend (`backend/`):** the same Flask + `ifcopenshell` service from the earlier Fase 2a work (`backend/app.py`, `backend/ifc_ops.py`) still exists and still works standalone, but is no longer wired to the frontend's "Bekreft" buttons. The primary tool for Nivå 1 is **`backend/kjor_ko.py`**, a plain CLI that reads a downloaded queue `.json` and a local IFC file and calls the same `ifc_ops.behandle_items()` — no server, no HTTP, just `python kjor_ko.py <ifc_fil> <ko_fil>`.

### Why Nivå 1 (not the original full-automation plan)

The original ask was full automation: click in the TC panel → vimpel is written → new file version auto-uploads to the project. Investigating that (see git history / prior session) surfaced two hard requirements that are outside this repo's control:
1. Trimble Connect's client-side Workspace API (what `app.js` uses) has **no** file-editing or file-versioning methods — that only exists in Trimble's separate server-to-server REST API.
2. That REST API requires an **OAuth app registration** (via Trimble's Integrations page or `connect-support@trimble.com` for external developers) plus a non-interactive backend that re-authenticates via a stored refresh token **at least every 9 days** (Trimble Connect has no Client Credentials / pure machine-to-machine grant) — meaning a real always-on, securely-configured server, not just "some code."

Kåre was unsure whether he currently has the organizational access/authority to register a Trimble integration or stand up always-on hosting, and didn't want to commit to that path yet. Rather than shelve the whole extension, we descoped to **Nivå 1**: keep everything that adds real value with zero new infrastructure (browsing the model, resolving GUIDs/names automatically, structuring the merknad payload correctly) and accept that downloading the file, running `kjor_ko.py`, and uploading the new version stay manual — the same manual steps as today's `D:\SOS-Kolbotn\app` workflow, just without having to hunt down GUIDs by hand.

**If OAuth/hosting access becomes available later**, re-enabling full automation is a small, well-scoped change: swap `downloadQueue()` in `app.js` for a `fetch()` to `backend/app.py`'s existing `/api/vimpel` / `/api/fjern-vimpel` endpoints (already built and tested — see "How the backend was tested" below), and extend `backend/app.py` to fetch/upload files via the TC REST API instead of a local `IFC_FIL` path. The `ifc_ops.py` editing logic itself would not change at all.

### How the backend was tested

No Trimble Connect REST API integration exists, so this couldn't be tested against a real TC project. Instead: copied a real model (`D:\SOS-Kolbotn\ifc\arbeidsunderlag\SOS_20KOL_F_RIB.ifc`) to a scratch location and ran both `backend/app.py` (via `curl`, and via `fetch()` from an actual browser context to confirm CORS works) and `backend/kjor_ko.py` against it, then re-opened the result with `ifcopenshell` to check the proxy count and pset contents. Confirmed: add is idempotent (replaces, doesn't duplicate), remove works, pset has all 7 fields on both the vimpel and the source element, and `kjor_ko.py`'s exit code reflects per-item success/failure.

The vimpel edit was also verified visually — a queue item built by the deployed extension in a real TC session was run through `kjor_ko.py` against the actual downloaded IFC file, and the result opened in Solibri showed the flag geometry in place with the correct `NCC-Produksjon` pset values. The `farge` (color) type was verified the same programmatic way as vimpel (`ifcopenshell.by_type("IfcStyledItem")` inspection, RGB values matched the chosen hex) but not yet re-verified visually in a viewer after this addition.

### How the frontend was verified live (2026-07-06, "Kåre Testmappe" project)

Deployed to GitHub Pages and added as a Custom Extension in a real Trimble Connect project. This surfaced a real bug the local-only testing couldn't catch: `checkRole()`'s original `members.find((m) => m.id === currentUser.id)` never matched, even for an actual project admin. Debugging via the browser's DevTools console (reading `document.getElementById('log').textContent` in the extension's iframe — not the TC host page, which has its own unrelated console noise) showed why: `UserAPI.getUser().id` (a global Trimble Identity UUID, e.g. `8a0c0e7a-a2d8-4203-a7db-4dcc98ae4961`) and `ProjectAPI.getMembers()[].id` (e.g. `JmBBHSsdFKY`) are **two different ID namespaces** for the same person — confirmed by matching email addresses across both. Fixed by falling back to a case-insensitive email match (see `checkRole()` below), and by logging the full member list on every run rather than just the current user's outcome, so any future mismatch is diagnosable without re-guessing.

Also confirmed live: `role` comes back as the string `"ADMIN"` (not e.g. `"admin"` or a numeric code) and `companyAdmin` can be `false` even for a genuine project admin — so the `isAdmin` check needs both the `companyAdmin` flag and the `role` regex match; neither alone is reliable for every user. With the email-fallback fix deployed, the full flow (connect → role check → admin buttons enabled → element selection resolves GUID/name → add/remove to queue → download `.json`) was confirmed working end-to-end in the real TC session.

**Gotcha for next time:** GitHub Pages caches assets for ~15 minutes (`Expires` header). After pushing a fix, a hard refresh of the *whole Trimble Connect browser tab* (Ctrl+Shift+R) is needed before re-testing — reloading just the extension panel isn't enough, since the iframe's cached `app.js` can still be served from the browser's HTTP cache.

## Architecture (frontend)

Everything lives in two files, same split as the "Søk Armering" reference project:

- **`index.html`** — markup, inline `<style>`, loads `vendor/trimbleconnect.workspace.api.js` then `app.js`.
- **`app.js`** — all logic:
  1. `main()` calls `TrimbleConnectWorkspace.connect(window.parent, callback, 30000)` once on load, then `checkRole()`, then fetches `API.project.getProject().name` into `currentProjectName`.
  2. `checkRole()` calls `API.user.getUser()` for the current user's id/email, and `API.project.getMembers()` for the project's member list (each entry has `id`/`email`/`role`/`companyAdmin`). Matches by id first, falls back to a case-insensitive email match — **required** in practice, since `UserAPI.getUser().id` and a member's `id` are different ID namespaces for the same person (confirmed live, see "How the frontend was verified live" below). Sets the module-level `isAdmin` flag from `companyAdmin || /admin/i.test(role)` (confirmed live: `role` comes back as `"ADMIN"`, and `companyAdmin` can be `false` for a real admin, so both checks are needed). Logs the full member list on every run for future diagnosability.
  3. `handleViewerSelection()` (fed by `viewer.onSelectionChanged`, guarded by `origin.isSelf` exactly like Søk Armering to avoid feedback loops) resolves **every** selected element into `currentSelection` (an array, possibly empty) — batched per `modelId` (one `convertToObjectIds`/`getObjectProperties` call per model, not per element) and matched back up by the `id` field on each returned `ObjectProperties` entry (not array position — that ordering isn't documented as guaranteed). `updateActionButtons()` gates vimpel actions to `currentSelection.length === 1` and color actions to `length >= 1`.
  4. The vimpel form (`openVimpelForm`/`closeVimpelForm`) and the farge form (`openFargeForm`/`closeFargeForm`, opened by clicking one of the 5 `.farge-btn` swatches) both collect a required free-text `merknad`.
  5. `submitVimpelForm()` / `removeVimpel()` build a single queue-item-shaped payload (`{type: "vimpel", guid, merknad, utfort_av, prosjekt}` / `{type: "fjern-vimpel", guid}`) from `currentSelection[0]` and call `addToQueue(payload, label)`. `submitFargeForm()` instead loops over **all** of `currentSelection`, adding one `{type: "farge", guid, farge: hex, merknad, utfort_av, prosjekt}` item per element — so a multi-element color action can still be partially undone from the queue list afterward.
  6. `addToQueue()` pushes to the module-level `queue` array and calls `renderQueue()`, which draws the list (with per-item `×` remove buttons via `removeFromQueue()`) and enables/disables the download/clear buttons.
  7. `downloadQueue()` serializes `queue.map(q => q.item)` to a `Blob` and triggers a browser download (`merknader-ko-<timestamp>.json`) — this is the only "export" mechanism; there is no network call anywhere in this file.

## Architecture (backend — `backend/`)

- **`backend/ifc_ops.py`** — adapted from `D:\SOS-Kolbotn\app\ifc_ops.py`. `lag_vimpel()` (stang+flagg geometry) and `fargelegg_element()` (direct element coloring — handles both the Tekla/`IfcMappedItem` and Revit/nested-items styling conventions) are ported unchanged. `legg_til_ncc_produksjon()` replaces `legg_til_sos_produksjon()`: same 7-field pset shape, but the `Prosjekt`/`Disiplin` values are passed in directly by the caller instead of being read from a `SOS-FELLES` source pset — this project has no such assumption to lean on. `behandle_items()` replaces `kjor_ko_sos()`: no per-file grouping/batching, since each call already targets one file; dispatches on `item["type"]` (`"vimpel"` / `"fjern-vimpel"` / `"farge"`); same atomic temp-file-then-`os.replace()` write. `_behandle_farge()` writes the pset only to the source element (unlike vimpel, there's no separate proxy object to also write it to).
- **`backend/kjor_ko.py`** — the Nivå 1 entry point: `python kjor_ko.py <ifc_fil> <ko_fil.json>`. Loads the queue JSON, calls `ifc_ops.behandle_items()`, prints per-item OK/FEIL, exits non-zero if anything failed. Type-agnostic — didn't need changes to support `farge`.
- **`backend/app.py`** — still present and still works (Flask + CORS, `POST /api/vimpel`, `POST /api/fjern-vimpel`, `POST /api/farge`, `GET /api/status`), but nothing in the frontend calls it right now. Kept as the re-enablement point if/when Kåre decides to pursue full automation (see "Why Nivå 1" above).

### Mapping from the old SOS-specific convention

| Dagens (SOS-Produksjon) | Nytt (NCC-Produksjon, generelt) |
|---|---|
| Pset `SOS-PRODUKSJON` | Pset `NCC-Produksjon` |
| `SOS_VIMPEL_<guid8>` navnekonvensjon | `NCC_VIMPEL_<guid8>` |
| `hent_sos_fra_element` (leser `SOS-FELLES` pset for prosjektnavn/fagkode) | Droppet — `prosjekt` sendes fra frontend (`API.project.getProject().name`), `disiplin` er tom inntil videre. Ikke alle NCC-prosjekter har en `SOS-FELLES` pset, så backend antar ikke at den finnes. |
| `legg_til_sos_felles` / `legg_til_bsdd_klassifisering` (SOS-Kolbotn-spesifikke ekstra psets/klassifisering på vimpelen) | Ikke portet — ikke del av dette prosjektets krav; kan legges til senere om et konkret NCC-prosjekt trenger det. |

## Deployment / testing loop

Same pattern as `D:\Trimble connect`:
- Repo: `https://github.com/kasterna/trimble-connect-merknader` (public, default branch `master` — GitHub Desktop named it that on publish, not `main`). Hosted on GitHub Pages at `https://kasterna.github.io/trimble-connect-merknader/`, which is what `manifest.json`'s `url`/`icon` point at. Trimble Connect fetches `manifest.json` once when an admin adds the Custom Extension; it does not auto-refresh on file changes.
- GitHub Pages free tier requires the repo to stay **public**.
- This machine has **no `gh` CLI** — pushing is done through GitHub Desktop by the user. After committing locally, tell the user to push via GitHub Desktop and wait ~1 minute for Pages to rebuild before re-testing in Trimble Connect. GitHub Pages then caches assets for ~15 minutes on top of that — see the live-verification gotcha above.
- `npm run dev` only proves the page loads without JS errors. Functional testing (role gating, selection, form) requires reloading the extension panel inside an actual Trimble Connect project — now done once, see "How the frontend was verified live" above.

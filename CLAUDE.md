# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Trimble Connect 3D Viewer side-panel extension ("Merknader") that lets project admins add or remove a **vimpel** (flag marker) annotation on a selected element — replacing today's manual workflow of running a local Flask app (`D:\SOS-Kolbotn\app`) and uploading the result by hand. See [README.md](README.md) for user-facing status and the role-gating explanation.

This is a **separate project/repo** from `D:\Trimble connect` ("Søk Armering") — each Trimble Connect extension Kåre builds gets its own repo, its own GitHub Pages URL, and its own manifest.json, even though the frontend skeleton is copied from that project.

## Current status: Nivå 1 (queue export, no server/OAuth) — done

Three ambition levels were scoped out for how the frontend hands off to the ifcopenshell edit (see "Why Nivå 1" below). **Nivå 1 is what's built and current:**

**Frontend (`app.js`):** connects to Trimble Connect, reads the current user's role from the project's own member list, gates the "Legg til vimpel"/"Fjern vimpel" UI to admins, lets an admin pick one element and fill in a merknad, and builds a queue-item payload for both actions — but instead of calling any backend automatically, it **appends the item to an in-page queue list** and lets the user download the whole queue as a `.json` file (`downloadQueue()`). No network call happens at all.

**Backend (`backend/`):** the same Flask + `ifcopenshell` service from the earlier Fase 2a work (`backend/app.py`, `backend/ifc_ops.py`) still exists and still works standalone, but is no longer wired to the frontend's "Bekreft" button. The primary tool for Nivå 1 is **`backend/kjor_ko.py`**, a plain CLI that reads a downloaded queue `.json` and a local IFC file and calls the same `ifc_ops.behandle_items()` — no server, no HTTP, just `python kjor_ko.py <ifc_fil> <ko_fil>`.

### Why Nivå 1 (not the original full-automation plan)

The original ask was full automation: click in the TC panel → vimpel is written → new file version auto-uploads to the project. Investigating that (see git history / prior session) surfaced two hard requirements that are outside this repo's control:
1. Trimble Connect's client-side Workspace API (what `app.js` uses) has **no** file-editing or file-versioning methods — that only exists in Trimble's separate server-to-server REST API.
2. That REST API requires an **OAuth app registration** (via Trimble's Integrations page or `connect-support@trimble.com` for external developers) plus a non-interactive backend that re-authenticates via a stored refresh token **at least every 9 days** (Trimble Connect has no Client Credentials / pure machine-to-machine grant) — meaning a real always-on, securely-configured server, not just "some code."

Kåre was unsure whether he currently has the organizational access/authority to register a Trimble integration or stand up always-on hosting, and didn't want to commit to that path yet. Rather than shelve the whole extension, we descoped to **Nivå 1**: keep everything that adds real value with zero new infrastructure (browsing the model, resolving GUIDs/names automatically, structuring the merknad payload correctly) and accept that downloading the file, running `kjor_ko.py`, and uploading the new version stay manual — the same manual steps as today's `D:\SOS-Kolbotn\app` workflow, just without having to hunt down GUIDs by hand.

**If OAuth/hosting access becomes available later**, re-enabling full automation is a small, well-scoped change: swap `downloadQueue()` in `app.js` for a `fetch()` to `backend/app.py`'s existing `/api/vimpel` / `/api/fjern-vimpel` endpoints (already built and tested — see "How the backend was tested" below), and extend `backend/app.py` to fetch/upload files via the TC REST API instead of a local `IFC_FIL` path. The `ifc_ops.py` editing logic itself would not change at all.

### How the backend was tested

No Trimble Connect REST API integration exists, so this couldn't be tested against a real TC project. Instead: copied a real model (`D:\SOS-Kolbotn\ifc\arbeidsunderlag\SOS_20KOL_F_RIB.ifc`) to a scratch location and ran both `backend/app.py` (via `curl`, and via `fetch()` from an actual browser context to confirm CORS works) and `backend/kjor_ko.py` against it, then re-opened the result with `ifcopenshell` to check the proxy count and pset contents. Confirmed: add is idempotent (replaces, doesn't duplicate), remove works, pset has all 7 fields on both the vimpel and the source element, and `kjor_ko.py`'s exit code reflects per-item success/failure.

## Architecture (frontend)

Everything lives in two files, same split as the "Søk Armering" reference project:

- **`index.html`** — markup, inline `<style>`, loads `vendor/trimbleconnect.workspace.api.js` then `app.js`.
- **`app.js`** — all logic:
  1. `main()` calls `TrimbleConnectWorkspace.connect(window.parent, callback, 30000)` once on load, then `checkRole()`, then fetches `API.project.getProject().name` into `currentProjectName`.
  2. `checkRole()` calls `API.user.getUser()` for the current user's id, and `API.project.getMembers()` for the project's member list (each entry has `role`/`companyAdmin`). Matches by id, sets the module-level `isAdmin` flag. **The exact `role` string values from a live project are unverified** — the raw value is logged on every run so it can be calibrated against real Trimble Connect data (same "can only really be tested inside TC" constraint as the rest of this app).
  3. `handleViewerSelection()` (fed by `viewer.onSelectionChanged`, guarded by `origin.isSelf` exactly like Søk Armering to avoid feedback loops) only accepts a **single** selected element — 0 or >1 clears `currentSelection` and logs why. For exactly one, it calls `viewer.convertToObjectIds()` for the IFC GUID and `viewer.getObjectProperties()` for the display name.
  4. The vimpel form (`openVimpelForm`/`closeVimpelForm`) collects a required free-text `merknad`.
  5. `submitVimpelForm()` / `removeVimpel()` build a queue-item-shaped payload (`{type: "vimpel", guid, merknad, utfort_av, prosjekt}` / `{type: "fjern-vimpel", guid}`) and call `addToQueue(payload, label)`.
  6. `addToQueue()` pushes to the module-level `queue` array and calls `renderQueue()`, which draws the list (with per-item `×` remove buttons via `removeFromQueue()`) and enables/disables the download/clear buttons.
  7. `downloadQueue()` serializes `queue.map(q => q.item)` to a `Blob` and triggers a browser download (`merknader-ko-<timestamp>.json`) — this is the only "export" mechanism; there is no network call anywhere in this file.

## Architecture (backend — `backend/`)

- **`backend/ifc_ops.py`** — adapted from `D:\SOS-Kolbotn\app\ifc_ops.py`. `lag_vimpel()` (stang+flagg geometry) is unchanged. `legg_til_ncc_produksjon()` replaces `legg_til_sos_produksjon()`: same 7-field pset shape, but the `Prosjekt`/`Disiplin` values are passed in directly by the caller instead of being read from a `SOS-FELLES` source pset — this project has no such assumption to lean on. `behandle_items()` replaces `kjor_ko_sos()`: no per-file grouping/batching, since each call already targets one file; same atomic temp-file-then-`os.replace()` write.
- **`backend/kjor_ko.py`** — the Nivå 1 entry point: `python kjor_ko.py <ifc_fil> <ko_fil.json>`. Loads the queue JSON, calls `ifc_ops.behandle_items()`, prints per-item OK/FEIL, exits non-zero if anything failed.
- **`backend/app.py`** — still present and still works (Flask + CORS, `POST /api/vimpel`, `POST /api/fjern-vimpel`, `GET /api/status`), but nothing in the frontend calls it right now. Kept as the re-enablement point if/when Kåre decides to pursue full automation (see "Why Nivå 1" above).

### Mapping from the old SOS-specific convention

| Dagens (SOS-Produksjon) | Nytt (NCC-Produksjon, generelt) |
|---|---|
| Pset `SOS-PRODUKSJON` | Pset `NCC-Produksjon` |
| `SOS_VIMPEL_<guid8>` navnekonvensjon | `NCC_VIMPEL_<guid8>` |
| `hent_sos_fra_element` (leser `SOS-FELLES` pset for prosjektnavn/fagkode) | Droppet — `prosjekt` sendes fra frontend (`API.project.getProject().name`), `disiplin` er tom inntil videre. Ikke alle NCC-prosjekter har en `SOS-FELLES` pset, så backend antar ikke at den finnes. |
| `legg_til_sos_felles` / `legg_til_bsdd_klassifisering` (SOS-Kolbotn-spesifikke ekstra psets/klassifisering på vimpelen) | Ikke portet — ikke del av dette prosjektets krav; kan legges til senere om et konkret NCC-prosjekt trenger det. |

## Deployment / testing loop

Same pattern as `D:\Trimble connect`:
- `manifest.json.url`/`.icon` will point at GitHub Pages once a repo exists (`https://kasterna.github.io/trimble-connect-merknader/...` — placeholder until the actual repo is created). Trimble Connect fetches `manifest.json` once when an admin adds the Custom Extension; it does not auto-refresh on file changes.
- GitHub Pages free tier requires the repo to stay **public**.
- This machine has **no `gh` CLI** — pushing is done through GitHub Desktop by the user. After committing locally, tell the user to push via GitHub Desktop and wait ~1 minute for Pages to rebuild before re-testing in Trimble Connect.
- `npm run dev` only proves the page loads without JS errors. Functional testing (role gating, selection, form) requires reloading the extension panel inside an actual Trimble Connect project.

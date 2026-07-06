# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Trimble Connect 3D Viewer side-panel extension ("Merknader") that lets project admins add or remove a **vimpel** (flag marker) annotation on a selected element — replacing today's manual workflow of running a local Flask app (`D:\SOS-Kolbotn\app`) and uploading the result by hand. See [README.md](README.md) for user-facing status and the role-gating explanation.

This is a **separate project/repo** from `D:\Trimble connect` ("Søk Armering") — each Trimble Connect extension Kåre builds gets its own repo, its own GitHub Pages URL, and its own manifest.json, even though the frontend skeleton is copied from that project.

## Current status: Fase 1 (frontend) and Fase 2a (backend logic) done, Fase 2b (Trimble Connect REST API) not started

**Fase 1 (done):** a deployable frontend extension — connects to Trimble Connect, reads the current user's role from the project's own member list, gates the "Legg til vimpel"/"Fjern vimpel" UI to admins, lets an admin pick one element and fill in a merknad, and builds the correct payload for both actions.

**Fase 2a (done, `backend/`):** a Flask + `ifcopenshell` service (`backend/app.py`, `backend/ifc_ops.py`) that actually performs the IFC edit — writes the vimpel geometry and `NCC-Produksjon` pset, atomically. `app.js`'s `postToBackend()` now does a real `fetch()` to this service (`BACKEND_URL` constant, defaults to `http://localhost:5003`). Verified end-to-end locally (see "How this was tested" below) against real SOS-Kolbotn IFC files: add is idempotent (replaces, doesn't duplicate), remove works, pset has all 7 fields on both the vimpel and the source element.

**Fase 2b (not started, needs its own session):** wiring the backend to an actual Trimble Connect project instead of a locally-configured file. This needs two decisions that were explicitly deferred by the user rather than picked unilaterally:
1. **Hosting environment** for the backend (must be reachable over HTTPS from a GitHub Pages-hosted iframe — calling `http://localhost` from an HTTPS page is blocked by mixed-content rules, so `BACKEND_URL` pointing at `localhost` only works when testing both halves on the same machine).
2. **Trimble Connect REST API credentials** (OAuth app registration in Trimble's developer portal) for server-to-server file download/upload — confirmed by reading the `trimble-connect-workspace-api` type definitions that the client-side Workspace API used in `app.js` has no file-versioning or IFC-editing methods at all; that only exists in TC's separate REST API. `backend/app.py` currently reads/writes one file named by the `IFC_FIL` env var (or `ifc_fil` in the request body) — swapping that for "download current version via TC REST API, run the same `ifc_ops.behandle_items()`, upload new version" is the only change Fase 2b needs to make; the ifcopenshell logic itself doesn't change.

Do not attempt to pick a hosting provider or design the TC REST API integration without checking in with the user first — this was called out explicitly during planning, not an oversight.

### How this was tested (Fase 2a)

No Trimble Connect REST API exists yet, so this couldn't be tested against a real TC project. Instead: copied a real model (`D:\SOS-Kolbotn\ifc\arbeidsunderlag\SOS_20KOL_F_RIB.ifc`) to a scratch location, ran `backend/app.py` with `IFC_FIL` pointed at the copy, and called `/api/vimpel` / `/api/fjern-vimpel` directly with `curl` and re-opened the result with `ifcopenshell` to check the proxy count and pset contents. Also called the backend from an actual browser context (via the frontend's dev server) to confirm CORS/`fetch()` works, not just server-to-server `curl`. None of this proves the eventual TC REST API integration works — only that the `ifc_ops.py` editing logic and the HTTP contract between `app.js` and `backend/app.py` are correct.

## Architecture (frontend, Fase 1)

Everything lives in two files, same split as the "Søk Armering" reference project:

- **`index.html`** — markup, inline `<style>`, loads `vendor/trimbleconnect.workspace.api.js` then `app.js`.
- **`app.js`** — all logic:
  1. `main()` calls `TrimbleConnectWorkspace.connect(window.parent, callback, 30000)` once on load, then `checkRole()`.
  2. `checkRole()` calls `API.user.getUser()` for the current user's id, and `API.project.getMembers()` for the project's member list (each entry has `role`/`companyAdmin`). Matches by id, sets the module-level `isAdmin` flag. **The exact `role` string values from a live project are unverified** — the raw value is logged on every run so it can be calibrated against real Trimble Connect data (same "can only really be tested inside TC" constraint as the rest of this app).
  3. `handleViewerSelection()` (fed by `viewer.onSelectionChanged`, guarded by `origin.isSelf` exactly like Søk Armering to avoid feedback loops) only accepts a **single** selected element — 0 or >1 clears `currentSelection` and logs why. For exactly one, it calls `viewer.convertToObjectIds()` for the IFC GUID and `viewer.getObjectProperties()` for the display name.
  4. The vimpel form (`openVimpelForm`/`closeVimpelForm`) collects a required free-text `merknad`.
  5. `submitVimpelForm()` / `removeVimpel()` build a queue-item-shaped payload (`{type: "vimpel", guid, merknad, utfort_av, prosjekt}` / `{type: "fjern-vimpel", guid}`) — `prosjekt` comes from `API.project.getProject().name`, fetched once in `main()` into `currentProjectName` — and call `postToBackend()`.
  6. `postToBackend()` POSTs to `BACKEND_URL + "/api/vimpel"` or `"/api/fjern-vimpel"` and surfaces the backend's `melding`/`error` via `setStatus()`/`log()`.

## Architecture (backend, Fase 2a — `backend/`)

- **`backend/app.py`** — Flask + CORS, two endpoints (`POST /api/vimpel`, `POST /api/fjern-vimpel`) plus `GET /api/status`. Each request resolves an IFC file path (`ifc_fil` in the body, falling back to the `IFC_FIL` env var) and calls `ifc_ops.behandle_items()` with a single queue item.
- **`backend/ifc_ops.py`** — adapted from `D:\SOS-Kolbotn\app\ifc_ops.py`. `lag_vimpel()` (stang+flagg geometry) is unchanged. `legg_til_ncc_produksjon()` replaces `legg_til_sos_produksjon()`: same 7-field pset shape, but the `Prosjekt`/`Disiplin` values are passed in directly by the caller instead of being read from a `SOS-FELLES` source pset — this project has no such assumption to lean on. `behandle_items()` replaces `kjor_ko_sos()`: no per-file grouping/batching, since each HTTP request already targets one file; same atomic temp-file-then-`os.replace()` write.

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

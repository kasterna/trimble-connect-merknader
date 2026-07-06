# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Trimble Connect 3D Viewer side-panel extension ("Merknader") that lets project admins add or remove a **vimpel** (flag marker) annotation on a selected element — replacing today's manual workflow of running a local Flask app (`D:\SOS-Kolbotn\app`) and uploading the result by hand. See [README.md](README.md) for user-facing status and the role-gating explanation.

This is a **separate project/repo** from `D:\Trimble connect` ("Søk Armering") — each Trimble Connect extension Kåre builds gets its own repo, its own GitHub Pages URL, and its own manifest.json, even though the frontend skeleton is copied from that project.

## Current status: Fase 1 (frontend) done, Fase 2 (backend) not started

**Fase 1 (this repo, done):** a deployable frontend extension — connects to Trimble Connect, reads the current user's role from the project's own member list, gates the "Legg til vimpel"/"Fjern vimpel" UI to admins, lets an admin pick one element and fill in a merknad, and builds the correct payload for both actions. `postToBackend()` in `app.js` is an intentional stub: it logs the payload and sets an error status instead of pretending anything was saved.

**Fase 2 (not started, needs its own session):** an actual backend service that performs the IFC edit and uploads a new version. This needs two decisions that were explicitly deferred by the user rather than picked unilaterally:
1. **Hosting environment** for a Python + `ifcopenshell` service (must be reachable over HTTPS from a GitHub Pages-hosted iframe — calling `http://localhost` from an HTTPS page is blocked by mixed-content rules, so the old local-Flask-app approach doesn't generalize to "any NCC project, any admin").
2. **Trimble Connect REST API credentials** (OAuth app registration in Trimble's developer portal) for server-to-server file download/upload — confirmed by reading the `trimble-connect-workspace-api` type definitions that the client-side Workspace API used here has no file-versioning or IFC-editing methods at all; that only exists in TC's separate REST API.

Do not attempt to pick a hosting provider or design the backend without checking in with the user first — this was called out explicitly during planning, not an oversight.

## Architecture (Fase 1)

Everything lives in two files, same split as the "Søk Armering" reference project:

- **`index.html`** — markup, inline `<style>`, loads `vendor/trimbleconnect.workspace.api.js` then `app.js`.
- **`app.js`** — all logic:
  1. `main()` calls `TrimbleConnectWorkspace.connect(window.parent, callback, 30000)` once on load, then `checkRole()`.
  2. `checkRole()` calls `API.user.getUser()` for the current user's id, and `API.project.getMembers()` for the project's member list (each entry has `role`/`companyAdmin`). Matches by id, sets the module-level `isAdmin` flag. **The exact `role` string values from a live project are unverified** — the raw value is logged on every run so it can be calibrated against real Trimble Connect data (same "can only really be tested inside TC" constraint as the rest of this app).
  3. `handleViewerSelection()` (fed by `viewer.onSelectionChanged`, guarded by `origin.isSelf` exactly like Søk Armering to avoid feedback loops) only accepts a **single** selected element — 0 or >1 clears `currentSelection` and logs why. For exactly one, it calls `viewer.convertToObjectIds()` for the IFC GUID and `viewer.getObjectProperties()` for the display name.
  4. The vimpel form (`openVimpelForm`/`closeVimpelForm`) collects a required free-text `merknad`.
  5. `submitVimpelForm()` / `removeVimpel()` build a queue-item-shaped payload (`{type: "vimpel", guid, merknad, utfort_av}` / `{type: "fjern-vimpel", guid}`) and call `postToBackend()`.
  6. `postToBackend()` is the Fase 2 integration point — currently a stub.

### Why the payload shape matches `ifc_ops.py`

The payload built in `submitVimpelForm`/`removeVimpel` deliberately mirrors the queue-item format that `D:\SOS-Kolbotn\app\ifc_ops.py`'s `kjor_ko_sos()` / `_behandle_vimpel()` / `_behandle_fjern_vimpel()` already consume, so that Fase 2's backend can reuse that logic almost unchanged. Mapping from the old SOS-specific convention to this project's general one:

| Dagens (SOS-Produksjon) | Nytt (NCC-Produksjon, generelt) |
|---|---|
| Pset `SOS-PRODUKSJON` | Pset `NCC-Produksjon` |
| `SOS_VIMPEL_<guid8>` navnekonvensjon | Beholdes, ev. `NCC_VIMPEL_<guid8>` |
| `hent_sos_fra_element` (leser `SOS-FELLES` pset for prosjektnavn/fagkode) | Må generaliseres — ikke alle NCC-prosjekter har en `SOS-FELLES` pset; Fase 2 backend must handle a missing source pset gracefully instead of assuming it's always there |

## Deployment / testing loop

Same pattern as `D:\Trimble connect`:
- `manifest.json.url`/`.icon` will point at GitHub Pages once a repo exists (`https://kasterna.github.io/trimble-connect-merknader/...` — placeholder until the actual repo is created). Trimble Connect fetches `manifest.json` once when an admin adds the Custom Extension; it does not auto-refresh on file changes.
- GitHub Pages free tier requires the repo to stay **public**.
- This machine has **no `gh` CLI** — pushing is done through GitHub Desktop by the user. After committing locally, tell the user to push via GitHub Desktop and wait ~1 minute for Pages to rebuild before re-testing in Trimble Connect.
- `npm run dev` only proves the page loads without JS errors. Functional testing (role gating, selection, form) requires reloading the extension panel inside an actual Trimble Connect project.

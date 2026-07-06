const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const readonlyNoteEl = document.getElementById("readonly-note");
const selectionEmptyEl = document.getElementById("selection-empty");
const selectionDetailsEl = document.getElementById("selection-details");
const selectionNameEl = document.getElementById("selection-name");
const selectionGuidEl = document.getElementById("selection-guid");
const addBtn = document.getElementById("add-btn");
const removeBtn = document.getElementById("remove-btn");
const vimpelForm = document.getElementById("vimpel-form");
const merknadInput = document.getElementById("merknad-input");
const formSubmitBtn = document.getElementById("form-submit-btn");
const formCancelBtn = document.getElementById("form-cancel-btn");

let API = null;
let isAdmin = false;
let currentUser = null; // { id, firstName, lastName, email }
let currentSelection = null; // { modelId, runtimeId, guid, name, class }

function log(msg) {
  const time = new Date().toLocaleTimeString();
  logEl.textContent += `[${time}] ${msg}\n`;
  logEl.scrollTop = logEl.scrollHeight;
}

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = cls || "";
}

/** Determines admin vs read-only access from Trimble Connect's own project membership,
 *  instead of a separate login system: matches the current user against the project's
 *  member list and reads their role/companyAdmin flag. The exact `role` string values
 *  returned by a live TC project aren't documented here, so we log the raw value for
 *  calibration the first time this runs against a real project. */
async function checkRole() {
  try {
    currentUser = await API.user.getUser();
    const members = await API.project.getMembers();
    const me = members.find((m) => m.id === currentUser.id);
    isAdmin = !!(me && (me.companyAdmin || (me.role && /admin/i.test(me.role))));
    log(
      `Rolle-sjekk: bruker=${currentUser.email || currentUser.id}, ` +
        `role="${me ? me.role : "(ikke funnet i medlemsliste)"}", ` +
        `companyAdmin=${me ? me.companyAdmin : "?"} → ${isAdmin ? "admin-tilgang" : "kun lesetilgang"}`
    );
  } catch (err) {
    isAdmin = false;
    log("Feil ved rollesjekk: " + err.message + " — viser kun lesetilgang.");
  }
  readonlyNoteEl.style.display = isAdmin ? "none" : "block";
  updateActionButtons();
}

function updateActionButtons() {
  const hasSelection = !!currentSelection;
  addBtn.disabled = !(isAdmin && hasSelection);
  removeBtn.disabled = !(isAdmin && hasSelection);
}

function renderSelection() {
  if (currentSelection) {
    selectionEmptyEl.style.display = "none";
    selectionDetailsEl.style.display = "block";
    selectionNameEl.textContent = currentSelection.name || currentSelection.class || "(uten navn)";
    selectionGuidEl.textContent = currentSelection.guid;
  } else {
    selectionEmptyEl.style.display = "block";
    selectionDetailsEl.style.display = "none";
  }
  updateActionButtons();
}

/** Handles a selection made in the 3D Viewer. Only a single selected element is
 *  supported for adding/removing a vimpel, mirroring the "søk armering" extension's
 *  origin.isSelf guard so our own setSelection() calls don't re-trigger this handler. */
async function handleViewerSelection(selection) {
  closeVimpelForm();

  const flat = [];
  for (const item of selection || []) {
    for (const runtimeId of item.objectRuntimeIds || []) {
      flat.push({ modelId: item.modelId, runtimeId });
    }
  }

  if (flat.length === 0) {
    currentSelection = null;
    renderSelection();
    return;
  }
  if (flat.length > 1) {
    currentSelection = null;
    renderSelection();
    log(`Valgte ${flat.length} elementer — velg nøyaktig ett element for vimpel-handlinger.`);
    return;
  }

  const { modelId, runtimeId } = flat[0];
  try {
    const [guid] = await API.viewer.convertToObjectIds(modelId, [runtimeId]);
    const [props] = await API.viewer.getObjectProperties(modelId, [runtimeId]);
    currentSelection = {
      modelId,
      runtimeId,
      guid,
      name: props && props.product && props.product.name,
      class: props && props.class,
    };
    renderSelection();
    log(`Valgt element: ${currentSelection.name || currentSelection.class || "(uten navn)"} (${guid})`);
  } catch (err) {
    currentSelection = null;
    renderSelection();
    log("Feil ved henting av GUID/egenskaper for valgt element: " + err.message);
  }
}

function openVimpelForm() {
  merknadInput.value = "";
  vimpelForm.style.display = "block";
  merknadInput.focus();
}

function closeVimpelForm() {
  vimpelForm.style.display = "none";
}

/** Fase 2 (egen økt): dette er stedet der payloaden postes til backend-tjenesten som
 *  gjør selve IFC-endringen (ifcopenshell) og laster opp ny versjon til Trimble Connect.
 *  Backend-arkitektur/hosting er ikke besluttet ennå, så her stubber vi kallet i stedet
 *  for å late som det lyktes. Payload-formatet matcher allerede kø-item-formatet i
 *  D:\SOS-Kolbotn\app\ifc_ops.py (kjor_ko_sos/_behandle_vimpel/_behandle_fjern_vimpel)
 *  slik at den koden kan gjenbrukes nesten uendret i Fase 2. */
async function postToBackend(payload) {
  log("Payload klar for backend (IKKE sendt ennå): " + JSON.stringify(payload));
  setStatus("Backend ikke koblet ennå ✘", "error");
}

async function submitVimpelForm() {
  const merknad = merknadInput.value.trim();
  if (!merknad) {
    merknadInput.focus();
    return;
  }
  const payload = {
    type: "vimpel",
    guid: currentSelection.guid,
    merknad,
    utfort_av: currentUser ? `${currentUser.firstName || ""} ${currentUser.lastName || ""}`.trim() || currentUser.email : "",
  };
  closeVimpelForm();
  await postToBackend(payload);
}

async function removeVimpel() {
  const payload = {
    type: "fjern-vimpel",
    guid: currentSelection.guid,
  };
  await postToBackend(payload);
}

addBtn.addEventListener("click", openVimpelForm);
removeBtn.addEventListener("click", removeVimpel);
formSubmitBtn.addEventListener("click", submitVimpelForm);
formCancelBtn.addEventListener("click", closeVimpelForm);

async function main() {
  try {
    API = await TrimbleConnectWorkspace.connect(
      window.parent,
      (event, args) => {
        if (event === "viewer.onSelectionChanged" && !(args.origin && args.origin.isSelf)) {
          handleViewerSelection(args.data);
        }
      },
      30000
    );
    window.API = API;
    setStatus("Tilkoblet Trimble Connect ✔", "ok");
    log("WorkspaceAPI.connect() lyktes.");
    await checkRole();
  } catch (err) {
    setStatus("Kunne ikke koble til Trimble Connect ✘", "error");
    log("Feil: " + err.message);
  }
}

main();

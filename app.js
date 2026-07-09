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
const revisjonenGjelderInput = document.getElementById("revisjonen-gjelder-input");
const vimpelCoordToggle = document.getElementById("vimpel-coord-toggle");
const vimpelCoordFields = document.getElementById("vimpel-coord-fields");
const vimpelXInput = document.getElementById("vimpel-x-input");
const vimpelYInput = document.getElementById("vimpel-y-input");
const vimpelZInput = document.getElementById("vimpel-z-input");
const formSubmitBtn = document.getElementById("form-submit-btn");
const formCancelBtn = document.getElementById("form-cancel-btn");
const queueEmptyEl = document.getElementById("queue-empty");
const queueListEl = document.getElementById("queue-list");
const queueCountEl = document.getElementById("queue-count");
const queueDownloadBtn = document.getElementById("queue-download-btn");
const queueClearBtn = document.getElementById("queue-clear-btn");
const fargeButtons = Array.from(document.querySelectorAll(".farge-btn"));
const fargeForm = document.getElementById("farge-form");
const fargeMerknadInput = document.getElementById("farge-merknad-input");
const fargeRevisjonenGjelderInput = document.getElementById("farge-revisjonen-gjelder-input");
const fargeFormSubmitBtn = document.getElementById("farge-form-submit-btn");
const fargeFormCancelBtn = document.getElementById("farge-form-cancel-btn");

let API = null;
let isAdmin = false;
let currentUser = null; // { id, firstName, lastName, email }
let currentProjectName = "";
let currentSelection = []; // [{ modelId, runtimeId, guid, name, class }, ...] — 0, 1 or many
let pendingFarge = null; // { hex, navn } — color picked, waiting for merknad confirmation
let queue = []; // { item, label } — item matches backend/ifc_ops.py's queue-item shape

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
    log(
      `Rolle-sjekk debug: currentUser.id=${currentUser.id}, currentUser.email=${currentUser.email}. ` +
        `Medlemsliste (${members.length}): ` +
        members.map((m) => `[id=${m.id}, email=${m.email}, role=${m.role}, companyAdmin=${m.companyAdmin}]`).join(", ")
    );
    const emailLower = (currentUser.email || "").toLowerCase();
    const me =
      members.find((m) => m.id === currentUser.id) ||
      members.find((m) => (m.email || "").toLowerCase() === emailLower);
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
  const single = currentSelection.length === 1;
  const any = currentSelection.length >= 1;
  addBtn.disabled = !(isAdmin && single);
  removeBtn.disabled = !(isAdmin && single);
  fargeButtons.forEach((btn) => {
    btn.disabled = !(isAdmin && any);
  });
}

function elementLabel(el) {
  return el.name || el.class || el.guid;
}

function renderSelection() {
  if (currentSelection.length === 0) {
    selectionEmptyEl.style.display = "block";
    selectionDetailsEl.style.display = "none";
  } else if (currentSelection.length === 1) {
    selectionEmptyEl.style.display = "none";
    selectionDetailsEl.style.display = "block";
    selectionNameEl.textContent = elementLabel(currentSelection[0]);
    selectionGuidEl.textContent = currentSelection[0].guid;
  } else {
    selectionEmptyEl.style.display = "none";
    selectionDetailsEl.style.display = "block";
    selectionNameEl.textContent = `${currentSelection.length} elementer valgt`;
    selectionGuidEl.textContent = currentSelection.map(elementLabel).join(", ");
  }
  updateActionButtons();
}

/** Handles a selection made in the 3D Viewer. "Legg til vimpel"/"Fjern vimpel" only
 *  work with exactly one selected element (see updateActionButtons), but "Fargelegg"
 *  supports any number — so this resolves GUID/name for every selected element, not
 *  just the first, batched per model for fewer API round-trips. Mirrors the
 *  "søk armering" extension's origin.isSelf guard so our own setSelection() calls
 *  don't re-trigger this handler. */
async function handleViewerSelection(selection) {
  closeVimpelForm();
  closeFargeForm();

  const flat = [];
  for (const item of selection || []) {
    for (const runtimeId of item.objectRuntimeIds || []) {
      flat.push({ modelId: item.modelId, runtimeId });
    }
  }

  if (flat.length === 0) {
    currentSelection = [];
    renderSelection();
    return;
  }

  const byModel = new Map();
  for (const entry of flat) {
    if (!byModel.has(entry.modelId)) byModel.set(entry.modelId, []);
    byModel.get(entry.modelId).push(entry.runtimeId);
  }

  try {
    const resolved = [];
    for (const [modelId, runtimeIds] of byModel.entries()) {
      const guids = await API.viewer.convertToObjectIds(modelId, runtimeIds);
      const propsList = await API.viewer.getObjectProperties(modelId, runtimeIds);
      const propsById = new Map(propsList.map((p) => [p.id, p]));
      runtimeIds.forEach((runtimeId, i) => {
        const props = propsById.get(runtimeId);
        resolved.push({
          modelId,
          runtimeId,
          guid: guids[i],
          name: props && props.product && props.product.name,
          class: props && props.class,
        });
      });
    }
    currentSelection = resolved;
    renderSelection();
    log(`Valgt ${resolved.length} element(er): ` + resolved.map(elementLabel).join(", "));
  } catch (err) {
    currentSelection = [];
    renderSelection();
    log("Feil ved henting av GUID/egenskaper for valgt element: " + err.message);
  }
}

function openVimpelForm() {
  merknadInput.value = "";
  revisjonenGjelderInput.value = "";
  vimpelCoordToggle.checked = false;
  vimpelXInput.value = "";
  vimpelYInput.value = "";
  vimpelZInput.value = "";
  vimpelCoordFields.style.display = "none";
  vimpelForm.style.display = "block";
  merknadInput.focus();
}

function closeVimpelForm() {
  vimpelForm.style.display = "none";
}

function toggleVimpelCoordFields() {
  vimpelCoordFields.style.display = vimpelCoordToggle.checked ? "flex" : "none";
  if (vimpelCoordToggle.checked) vimpelXInput.focus();
}

/** Legger en payload i den lokale køen i stedet for å sende den til en backend.
 *  Automatisk opplasting til Trimble Connect er ikke bygget (se CLAUDE.md, "Nivå 1"):
 *  dette krever ingen server eller OAuth. Payload-formatet matcher kø-item-formatet i
 *  backend/ifc_ops.py sin behandle_items() — "Last ned kø" gir en .json du kjører
 *  lokalt med backend/kjor_ko.py mot en nedlastet kopi av IFC-fila. */
function addToQueue(item, label) {
  queue.push({ item, label });
  renderQueue();
  log("Lagt i kø: " + label);
}

function removeFromQueue(index) {
  queue.splice(index, 1);
  renderQueue();
}

function renderQueue() {
  queueListEl.innerHTML = "";
  const isEmpty = queue.length === 0;
  queueEmptyEl.style.display = isEmpty ? "block" : "none";
  queueDownloadBtn.disabled = isEmpty;
  queueClearBtn.disabled = isEmpty;
  queueCountEl.textContent = String(queue.length);

  queue.forEach(({ label }, index) => {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.className = "queue-label";
    span.textContent = label;
    span.title = label;
    const removeBtnEl = document.createElement("button");
    removeBtnEl.textContent = "×";
    removeBtnEl.title = "Fjern fra kø";
    removeBtnEl.addEventListener("click", () => removeFromQueue(index));
    li.appendChild(span);
    li.appendChild(removeBtnEl);
    queueListEl.appendChild(li);
  });
}

function downloadQueue() {
  const items = queue.map((q) => q.item);
  const blob = new Blob([JSON.stringify(items, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  a.href = url;
  a.download = `merknader-ko-${stamp}.json`;
  a.click();
  URL.revokeObjectURL(url);
  log(`Lastet ned kø med ${items.length} post(er).`);
}

function clearQueue() {
  queue = [];
  renderQueue();
}

function utfortAv() {
  return currentUser ? `${currentUser.firstName || ""} ${currentUser.lastName || ""}`.trim() || currentUser.email : "";
}

function submitVimpelForm() {
  const merknad = merknadInput.value.trim();
  if (!merknad) {
    merknadInput.focus();
    return;
  }
  const revisjonenGjelder = revisjonenGjelderInput.value.trim();
  if (!revisjonenGjelder) {
    revisjonenGjelderInput.focus();
    return;
  }
  let koordinater = null;
  if (vimpelCoordToggle.checked) {
    const x = parseFloat(vimpelXInput.value);
    const y = parseFloat(vimpelYInput.value);
    const z = parseFloat(vimpelZInput.value);
    if (Number.isNaN(x) || Number.isNaN(y) || Number.isNaN(z)) {
      log("Ugyldige koordinater — fyll ut X, Y og Z (mm), eller fjern haken for å bruke senter av objekt.");
      (Number.isNaN(x) ? vimpelXInput : Number.isNaN(y) ? vimpelYInput : vimpelZInput).focus();
      return;
    }
    koordinater = { x, y, z };
  }
  const sel = currentSelection[0];
  const payload = {
    type: "vimpel",
    guid: sel.guid,
    merknad,
    revisjonen_gjelder: revisjonenGjelder,
    utfort_av: utfortAv(),
    prosjekt: currentProjectName,
  };
  if (koordinater) payload.koordinater = koordinater;
  const label = koordinater
    ? `Vimpel: ${elementLabel(sel)} — "${merknad}" @ (${koordinater.x}, ${koordinater.y}, ${koordinater.z})`
    : `Vimpel: ${elementLabel(sel)} — "${merknad}"`;
  closeVimpelForm();
  addToQueue(payload, label);
}

function removeVimpel() {
  const sel = currentSelection[0];
  const payload = {
    type: "fjern-vimpel",
    guid: sel.guid,
  };
  const label = `Fjern vimpel: ${elementLabel(sel)}`;
  addToQueue(payload, label);
}

function openFargeForm(hex, navn) {
  pendingFarge = { hex, navn };
  fargeMerknadInput.value = "";
  fargeRevisjonenGjelderInput.value = "";
  fargeForm.style.display = "block";
  fargeMerknadInput.focus();
}

function closeFargeForm() {
  fargeForm.style.display = "none";
  pendingFarge = null;
}

/** Legger én kø-post per valgt element — slik at brukeren kan fjerne enkeltposter
 *  fra køen senere hvis f.eks. ett av flere elementer ble valgt ved en feil. Alle
 *  postene deler samme farge og merknad siden de kommer fra samme bekreftelse. */
function submitFargeForm() {
  const merknad = fargeMerknadInput.value.trim();
  if (!merknad) {
    fargeMerknadInput.focus();
    return;
  }
  const revisjonenGjelder = fargeRevisjonenGjelderInput.value.trim();
  if (!revisjonenGjelder) {
    fargeRevisjonenGjelderInput.focus();
    return;
  }
  const { hex, navn } = pendingFarge;
  for (const sel of currentSelection) {
    const payload = {
      type: "farge",
      guid: sel.guid,
      farge: hex,
      merknad,
      revisjonen_gjelder: revisjonenGjelder,
      utfort_av: utfortAv(),
      prosjekt: currentProjectName,
    };
    addToQueue(payload, `Fargelegg (${navn}): ${elementLabel(sel)} — "${merknad}"`);
  }
  closeFargeForm();
}

addBtn.addEventListener("click", openVimpelForm);
removeBtn.addEventListener("click", removeVimpel);
formSubmitBtn.addEventListener("click", submitVimpelForm);
formCancelBtn.addEventListener("click", closeVimpelForm);
vimpelCoordToggle.addEventListener("change", toggleVimpelCoordFields);
fargeButtons.forEach((btn) => {
  btn.addEventListener("click", () => openFargeForm(btn.dataset.hex, btn.dataset.navn));
});
fargeFormSubmitBtn.addEventListener("click", submitFargeForm);
fargeFormCancelBtn.addEventListener("click", closeFargeForm);
queueDownloadBtn.addEventListener("click", downloadQueue);
queueClearBtn.addEventListener("click", clearQueue);

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
    try {
      const project = await API.project.getProject();
      currentProjectName = project.name || "";
    } catch (err) {
      log("Feil ved henting av prosjektnavn: " + err.message);
    }
    await checkRole();
  } catch (err) {
    setStatus("Kunne ikke koble til Trimble Connect ✘", "error");
    log("Feil: " + err.message);
  }
}

main();

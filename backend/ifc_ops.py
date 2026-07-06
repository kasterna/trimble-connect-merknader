import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
import os
import tempfile
from datetime import date as _date_cls

VIMPEL_PREFIX = "NCC_VIMPEL_"
PSET_NAVN = "NCC-Produksjon"


def hex_til_rgb(hex_str):
    h = (hex_str or "#CC0000").lstrip("#")
    if len(h) < 6:
        h = h.ljust(6, "0")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def hent_skalafaktor(model):
    for unit in model.by_type("IfcSIUnit"):
        if unit.UnitType == "LENGTHUNIT" and unit.Prefix == "MILLI":
            return 1000.0
    return 1.0


def _pt(m, x, y, z):  return m.createIfcCartesianPoint([float(x), float(y), float(z)])
def _pt2(m, x, y):    return m.createIfcCartesianPoint([float(x), float(y)])
def _dir(m, x, y, z): return m.createIfcDirection([float(x), float(y), float(z)])


def _legg_farge(model, geom_item, r, g, b):
    col  = model.createIfcColourRgb(None, float(r), float(g), float(b))
    rend = model.createIfcSurfaceStyleRendering(col, None, None, None, None, None, None, None, "FLAT")
    sty  = model.createIfcSurfaceStyle(None, "BOTH", [rend])
    psa  = model.createIfcPresentationStyleAssignment([sty])
    model.createIfcStyledItem(geom_item, [psa], None)


def legg_til_ncc_produksjon(model, element, merknad, status, disiplin, prosjekt, utfort_av, revisjonsnummer, revisjonsdato):
    """Legger til eller oppdaterer NCC-Produksjon pset på et element.

    Generalisert versjon av dagens SOS-PRODUKSJON (D:\\SOS-Kolbotn\\app\\ifc_ops.py):
    samme syv felter, men uten avhengighet til en "SOS-FELLES"-kildepset som ikke
    finnes i alle NCC-prosjekter. Prosjekt/Disiplin sendes inn direkte fra kallet
    (typisk hentet fra Trimble Connect-prosjektet i frontend) i stedet for å bli lest
    ut av modellen.
    """
    for rel in list(model.by_type("IfcRelDefinesByProperties")):
        if element in rel.RelatedObjects:
            ps = rel.RelatingPropertyDefinition
            if hasattr(ps, "Name") and ps.Name == PSET_NAVN:
                try:
                    model.remove(ps)
                    model.remove(rel)
                except Exception:
                    pass
                break
    pset = ifcopenshell.api.run("pset.add_pset", model, product=element, name=PSET_NAVN)
    ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={
        "Merknad":         merknad or "",
        "Status":          status or "Apen",
        "Disiplin":        disiplin or "",
        "Prosjekt":        prosjekt or "",
        "Utfort_av":       utfort_av or "",
        "Revisjonsnummer": revisjonsnummer or "",
        "Revisjonsdato":   revisjonsdato or "",
    })


def fargelegg_element(model, element, r, g, b):
    """Fargelegger et elements egen geometri direkte (ingen ny geometri/proxy).
    Portert uendret fra D:\\SOS-Kolbotn\\app\\ifc_ops.py — håndterer at ulike
    IFC-eksportverktøy styler geometrien forskjellig:
    - Revit (RIB): IfcStyledItem på items INNI mapped rep (IfcMappedItem ignoreres)
    - Tekla (TELE): IfcStyledItem direkte på IfcMappedItem (brep-items ignoreres)
    Vi styler BEGGE steder for å dekke alle viewere (Solibri, Trimble, etc.).
    Returnerer (bool, str) — True/"" ved suksess, False/"årsak" ved feil.
    """
    if not element.Representation:
        return False, "Ingen Representation"

    reps = list(element.Representation.Representations or [])

    body = next(
        (rep for rep in reps
         if rep.RepresentationIdentifier == "Body" and rep.Items),
        None,
    )
    if body is None:
        _skip = {"Axis", "FootPrint", "Survey", "CoG", "Profile", "Reference"}
        body = next(
            (rep for rep in reps
             if (rep.RepresentationIdentifier or "") not in _skip and rep.Items),
            None,
        )

    if not body:
        ids = [rep.RepresentationIdentifier for rep in reps]
        return False, "Ingen body-rep. Tilgjengelige: " + str(ids)

    if not body.Items:
        return False, "Body-rep har ingen items (id=" + str(body.RepresentationIdentifier) + ")"

    geom_items = []
    for item in body.Items:
        if item.is_a("IfcMappedItem"):
            geom_items.append(item)
            try:
                mapped_rep = item.MappingSource.MappedRepresentation
                if mapped_rep and mapped_rep.Items:
                    geom_items.extend(mapped_rep.Items)
            except Exception:
                pass
        else:
            geom_items.append(item)

    if not geom_items:
        return False, "Ingen geom_items etter IfcMappedItem-traversal"

    for geom_item in geom_items:
        for si in list(model.by_type("IfcStyledItem")):
            if si.Item and si.Item.id() == geom_item.id():
                model.remove(si)
        _legg_farge(model, geom_item, r, g, b)
    return True, ""


def lag_vimpel(model, element, vx, vy, vz, fr, fg, fb, vimpel_navn):
    """Grå stang + farget flagg, plassert ved (vx, vy, vz) i modellens native enhet.
    Uendret geometri-oppskrift fra dagens SOS-Produksjon ifc_ops.py."""
    s = hent_skalafaktor(model)

    stang_prof = model.createIfcCircleProfileDef(
        "AREA", None,
        model.createIfcAxis2Placement2D(_pt2(model, 0, 0), None),
        0.004 * s,
    )
    stang_plac = model.createIfcAxis2Placement3D(
        _pt(model, 0, 0, 0), _dir(model, 0, 0, 1), _dir(model, 1, 0, 0)
    )
    stang = model.createIfcExtrudedAreaSolid(stang_prof, stang_plac, _dir(model, 0, 0, 1), 1.0 * s)
    _legg_farge(model, stang, 0.6, 0.6, 0.6)

    flagg_prof = model.createIfcRectangleProfileDef(
        "AREA", None,
        model.createIfcAxis2Placement2D(_pt2(model, 0.104 * s, 0), None),
        0.20 * s, 0.004 * s,
    )
    flagg_plac = model.createIfcAxis2Placement3D(
        _pt(model, 0, 0, 0.85 * s), _dir(model, 0, 0, 1), _dir(model, 1, 0, 0)
    )
    flagg = model.createIfcExtrudedAreaSolid(flagg_prof, flagg_plac, _dir(model, 0, 0, 1), 0.15 * s)
    _legg_farge(model, flagg, fr, fg, fb)

    ctx = next(
        (c for c in model.by_type("IfcGeometricRepresentationContext") if c.ContextType == "Model"),
        model.by_type("IfcGeometricRepresentationContext")[0],
    )
    body_rep   = model.createIfcShapeRepresentation(ctx, "Body", "SolidModel", [stang, flagg])
    prod_shape = model.createIfcProductDefinitionShape(None, None, [body_rep])

    plac_3d = model.createIfcAxis2Placement3D(
        _pt(model, vx, vy, vz),
        _dir(model, 0, 0, 1),
        _dir(model, 1, 0, 0),
    )
    lp = model.createIfcLocalPlacement(None, plac_3d)

    proxy = ifcopenshell.api.run("root.create_entity", model,
                                 ifc_class="IfcBuildingElementProxy", name=vimpel_navn)
    proxy.ObjectPlacement = lp
    proxy.Representation  = prod_shape

    for rel in model.by_type("IfcRelContainedInSpatialStructure"):
        if element in rel.RelatedElements:
            rel.RelatedElements = list(rel.RelatedElements) + [proxy]
            break
    return proxy


def _behandle_vimpel(model, item, dato):
    """item: {guid, merknad, utfort_av, disiplin?, prosjekt?, revisjonsnummer?, flagg_farge?}"""
    guid = item.get("guid", "")
    try:
        element = model.by_guid(guid)
    except Exception:
        element = None
    if not element:
        return False, "GUID ikke funnet: " + guid

    utfort_av = item.get("utfort_av", "") or "NCC-Produksjon"
    merknad   = item.get("merknad", "")
    disiplin  = item.get("disiplin", "")
    prosjekt  = item.get("prosjekt", "")
    revnr     = item.get("revisjonsnummer", "")

    # create_shape returnerer alltid i SI-meter (ifcopenshell normaliserer internt).
    # Bruk verdskoordinater og konverter til modellens native eining (mm for Revit/RIB).
    gs = ifcopenshell.geom.settings()
    gs.set(gs.USE_WORLD_COORDS, True)
    try:
        shape = ifcopenshell.geom.create_shape(gs, element)
        verts = shape.geometry.verts
        xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
        if not xs:
            return False, "Ingen geometri"
        vx = (min(xs) + max(xs)) / 2
        vy = (min(ys) + max(ys)) / 2
        vz = (min(zs) + max(zs)) / 2
    except Exception as e:
        return False, "Geometri-feil: " + str(e)

    s = hent_skalafaktor(model)
    vx *= s
    vy *= s
    vz *= s

    vimpel_navn = VIMPEL_PREFIX + guid[:8]
    for existing in list(model.by_type("IfcBuildingElementProxy")):
        if existing.Name == vimpel_navn:
            try:
                ifcopenshell.api.run("root.remove_product", model, product=existing)
            except Exception:
                pass
            break

    fr, fg, fb = hex_til_rgb(item.get("flagg_farge") or "#CC0000")
    proxy = lag_vimpel(model, element, vx, vy, vz, fr, fg, fb, vimpel_navn)

    legg_til_ncc_produksjon(model, proxy,   merknad, "Apen", disiplin, prosjekt, utfort_av, revnr, dato)
    legg_til_ncc_produksjon(model, element, merknad, "Apen", disiplin, prosjekt, utfort_av, revnr, dato)

    return True, "Vimpel for " + guid[:12] + "... @ ({:.1f}, {:.1f}, {:.1f})".format(vx, vy, vz)


def _behandle_fjern_vimpel(model, item):
    guid = item.get("guid", "")
    if not guid:
        return False, "Mangler GUID"
    navn = VIMPEL_PREFIX + guid[:8]
    for proxy in list(model.by_type("IfcBuildingElementProxy")):
        if getattr(proxy, "Name", None) == navn:
            ifcopenshell.api.run("root.remove_product", model, product=proxy)
            return True, "Fjernet vimpel " + navn + " for " + guid[:12] + "..."
    return False, "Ingen vimpel funnet for " + guid[:12] + "..."


def _behandle_farge(model, item, dato):
    """item: {guid, farge, merknad, utfort_av, disiplin?, prosjekt?, revisjonsnummer?}
    Fargelegger elementet direkte (ingen ny geometri) og skriver NCC-Produksjon på det —
    i motsetning til vimpel er det ingen egen proxy å skrive pset-et på i tillegg."""
    guid = item.get("guid", "")
    try:
        element = model.by_guid(guid)
    except Exception:
        element = None
    if not element:
        return False, "GUID ikke funnet: " + guid

    farge_hex = item.get("farge") or "#CC0000"
    utfort_av = item.get("utfort_av", "") or "NCC-Produksjon"
    merknad   = item.get("merknad", "")
    disiplin  = item.get("disiplin", "")
    prosjekt  = item.get("prosjekt", "")
    revnr     = item.get("revisjonsnummer", "")

    r, g, b = hex_til_rgb(farge_hex)
    farge_ok, farge_info = fargelegg_element(model, element, r, g, b)
    if not farge_ok:
        return False, "Fargelegging feilet: " + farge_info

    legg_til_ncc_produksjon(model, element, merknad, "Apen", disiplin, prosjekt, utfort_av, revnr, dato)

    return True, "Farget " + guid[:12] + "... " + farge_hex


def behandle_items(kilde_sti, items, output_sti=None):
    """Åpner IFC-fila på kilde_sti, kjører items ("vimpel" / "fjern-vimpel") i rekkefølge,
    og skriver resultatet atomisk (temp-fil + rename) til output_sti (default: samme fil).

    Enklere enn dagens kjor_ko_sos i D:\\SOS-Kolbotn\\app\\ifc_ops.py, som grupperer
    items per IFC-fil for batch-kjøring over mange filer samtidig — denne backend-en
    betjener én ekstensjon-forespørsel om gangen mot én allerede identifisert fil,
    så gruppering på tvers av filer trengs ikke.
    """
    output_sti = output_sti or kilde_sti
    dato = _date_cls.today().strftime("%Y-%m-%d")
    model = ifcopenshell.open(kilde_sti)

    resultater = []
    for item in items:
        try:
            if item.get("type") == "vimpel":
                ok, melding = _behandle_vimpel(model, item, dato)
            elif item.get("type") == "fjern-vimpel":
                ok, melding = _behandle_fjern_vimpel(model, item)
            elif item.get("type") == "farge":
                ok, melding = _behandle_farge(model, item, dato)
            else:
                ok, melding = False, "Ukjent type: " + str(item.get("type"))
        except Exception as e:
            ok, melding = False, "Feil: " + str(e)
        resultater.append((ok, melding))

    output_mappe = os.path.dirname(output_sti) or "."
    os.makedirs(output_mappe, exist_ok=True)
    fd, tmp_sti = tempfile.mkstemp(suffix=".ifc", dir=output_mappe)
    os.close(fd)
    try:
        model.write(tmp_sti)
        os.replace(tmp_sti, output_sti)
    except Exception:
        try:
            os.unlink(tmp_sti)
        except OSError:
            pass
        raise

    return resultater

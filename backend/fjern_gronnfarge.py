"""Bulk-fjerner grønn element-styling (IfcStyledItem) fra en hel IFC-fil.

Uavhengig av utvalg i vieweren: går gjennom ALLE IfcStyledItem i modellen,
finner de som styler med en flat overflatefarge der grønnkanalen tydelig
dominerer over rødt og blått (dekker både extensionens egen "Grønn"
(#2E7D32) og andre grønnnyanser fra andre fargeleggingsverktøy, f.eks.
rene/lyse grønne som #00CC00), og fjerner dem — samt de tilhørende
stildefinisjonene (IfcPresentationStyleAssignment/IfcSurfaceStyle/
IfcSurfaceStyleRendering/IfcColourRgb) hvis de ikke lenger er referert av
noe annet element etterpå.

Bruk: python fjern_gronnfarge.py <ifc_fil>
Skriver resultatet atomisk tilbake til samme fil (temp-fil + rename) —
bruk en kopi, ikke originalen fra Trimble Connect.
"""
import os
import sys
import tempfile

import ifcopenshell

TERSKEL = 0.15  # hvor mye grønnkanalen må dominere over rødt/blått (0-1) for å telle som "grønn"


def _er_gronn(r, g, b):
    return (g - r) > TERSKEL and (g - b) > TERSKEL


def _fjern_hvis_ubrukt(model, entity):
    """Fjerner en stil-entitet bare hvis ingenting annet i modellen refererer til den lenger."""
    if entity is None:
        return
    try:
        if not model.get_inverse(entity):
            model.remove(entity)
    except Exception:
        pass


def _surface_styles_i(style_entry):
    """style_entry er ett element fra IfcStyledItem.Styles — enten en
    IfcPresentationStyleAssignment (IFC2X3-mønster, som denne extensionen skriver)
    eller direkte en IfcSurfaceStyle (IFC4-mønster). Returnerer (wrapper_or_None, [IfcSurfaceStyle...])."""
    if style_entry.is_a("IfcPresentationStyleAssignment"):
        return style_entry, [s for s in style_entry.Styles if s.is_a("IfcSurfaceStyle")]
    if style_entry.is_a("IfcSurfaceStyle"):
        return None, [style_entry]
    return None, []


def fjern_gronn_styling(model):
    """Returnerer antall IfcStyledItem som ble fjernet fordi de matchet grønnfargen."""
    fjernet = 0
    for si in list(model.by_type("IfcStyledItem")):
        match = False
        for style_entry in list(si.Styles or []):
            psa, surface_styles = _surface_styles_i(style_entry)
            for sty in surface_styles:
                for rend in list(sty.Styles or []):
                    colour = getattr(rend, "SurfaceColour", None)
                    if colour is None or not colour.is_a("IfcColourRgb"):
                        continue
                    if _er_gronn(colour.Red, colour.Green, colour.Blue):
                        match = True
                        # Fjern utenfra og inn (si -> psa -> sty -> rend -> colour) slik at
                        # get_inverse-sjekken lenger inn i kjeden ser at det ytre laget
                        # allerede er borte — ellers ser en delt sty/rend fortsatt "i bruk"
                        # ut selv når begge StyledItem-referansene til den er fjernet.
                        model.remove(si)
                        if psa:
                            _fjern_hvis_ubrukt(model, psa)
                        _fjern_hvis_ubrukt(model, sty)
                        _fjern_hvis_ubrukt(model, rend)
                        _fjern_hvis_ubrukt(model, colour)
                        break
                if match:
                    break
            if match:
                break
        if match:
            fjernet += 1
    return fjernet


def main():
    if len(sys.argv) != 2:
        print("Bruk: python fjern_gronnfarge.py <ifc_fil>")
        sys.exit(1)

    sti = sys.argv[1]
    model = ifcopenshell.open(sti)
    antall = fjern_gronn_styling(model)
    print(f"Fjernet grønn styling fra {antall} element(er).")

    mappe = os.path.dirname(sti) or "."
    fd, tmp_sti = tempfile.mkstemp(suffix=".ifc", dir=mappe)
    os.close(fd)
    try:
        model.write(tmp_sti)
        os.replace(tmp_sti, sti)
    except Exception:
        try:
            os.unlink(tmp_sti)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()

# Merknader

En Trimble Connect-extension (side-panel i 3D Viewer) som lar prosjekt-admins legge til eller fjerne en **vimpel**-merknad på et valgt element, uten å gå via en lokal Flask-app og manuell filopplasting.

En vimpel er en liten IFC-geometri (grå stang + rødt flagg) plassert ved elementet, sammen med et egendefinert pset `NCC-Produksjon` (Merknad, Status, Disiplin, Prosjekt, Utført av, Revisjonsnummer, Revisjonsdato) skrevet på både vimpelen og kildeelementet.

Bygget etter samme mønster som ["Søk Armering"](https://github.com/kasterna/rebar-postliste).

## Status: Nivå 1 (kø-eksport, ingen server/OAuth) — verifisert i en ekte Trimble Connect-økt

Full automatikk (klikk i Trimble Connect → vimpel skrives → lastes automatisk opp som ny fil-versjon) krever et Trimble Connect REST API-oppsett med OAuth-registrering og en alltid-på server — se `CLAUDE.md` for hvorfor. Siden det er usikkert om/når det er tilgjengelig, er extensionen bygget for en enklere, men fortsatt nyttig arbeidsflyt uten noe av det:

Denne extensionen kan i dag:
- Koble seg til Trimble Connect og lese hvilken rolle innlogget bruker har i prosjektet (`ProjectAPI.getMembers()` + `UserAPI.getUser()`), og vise/skjule handlinger deretter.
- La en admin velge ett element i 3D-vieweren, og fylle ut en merknad i skjemaet "Legg til vimpel".
- Bygge riktig payload for både "Legg til vimpel" og "Fjern vimpel", og legge dem i en **kø-liste i panelet** (kan bygges opp over flere elementer i samme økt, fjerne enkeltposter, eller tømme alt).
- **Laste ned køen** som en `.json`-fil, klar til å kjøres lokalt med [backend/kjor_ko.py](backend/kjor_ko.py) (Flask+ifcopenshell-logikken som faktisk skriver vimpel-geometrien og `NCC-Produksjon`-pset-et — testet lokalt mot ekte SOS-Kolbotn-modeller).

Det som fortsatt er manuelt (som i dag med `D:\SOS-Kolbotn\app`):
- Laste ned IFC-filen fra Trimble Connect
- Kjøre `kjor_ko.py` lokalt mot fila + kø-fila
- Laste opp den redigerte fila som ny versjon i Trimble Connect sitt eget grensesnitt

**Testet 2026-07-06 i et ekte prosjekt ("Kåre Testmappe"):** tilkobling, rollesjekk (admin-tilgang riktig gjenkjent), elementvalg, kø-bygging og nedlasting av kø-fil fungerte alle som forventet — se `CLAUDE.md` for detaljene rundt rollesjekk-kalibreringen som måtte til.

Se `CLAUDE.md` for hva som skal til for å gå videre til full automatikk, og hvorfor det ble utsatt.

## Rollestyring

Ingen eget innloggingssystem. Extensionen leser gjeldende brukers rolle direkte fra Trimble Connect sin egen prosjekt-medlemsliste (`role`/`companyAdmin` per medlem), og faller tilbake på e-post-matching siden `UserAPI.getUser().id` og medlemslistens `id` viste seg å være to ulike ID-namespace i praksis (bekreftet i en ekte test). Alle andre enn admins får skrivebeskyttet visning (handlingsknappene er skjult/deaktivert, og en gul merknad forklarer hvorfor).

## Kjent begrensning (akseptert for v1)

Hvis to admins laster opp en endring til samme IFC-fil samtidig, kan den ene opplastingen overskrive den andre. Løses ikke i første versjon.

## Legge til i et Trimble Connect-prosjekt

1. Gå til **Project Settings → Extensions** i prosjektet
2. Velg **Add Custom Extension**
3. Lim inn manifest-URL-en: `https://kasterna.github.io/trimble-connect-merknader/manifest.json`
4. Aktiver extensionen og åpne den fra 3D Viewer-sidepanelet

## Lokal utvikling

```bash
npm install
npm run dev   # http-server på :8081 med --cors
```

Åpne `http://localhost:8081`. Som med "Søk Armering" gir dette kun en "laster uten feil"-sjekk — `WorkspaceAPI.connect()`, rollesjekk og elementvalg krever at siden faktisk kjører som iframe inni Trimble Connect.

`npm run dev` kjører nå med `-c-1` (deaktivert cache), nettopp fordi `http-server`s standard `cache-control: max-age=3600` ellers gjør at endringer i `app.js` ikke vises selv etter vanlig reload — hard-refresh (Ctrl+Shift+R) hvis du likevel ser gammel oppførsel.

For å kjøre en nedlastet kø mot en IFC-fil lokalt, se [backend/README.md](backend/README.md).

## Prosjektstruktur

```
index.html    – markup og styling
app.js        – all logikk (tilkobling, rollesjekk, valg, skjema, kø-bygging/nedlasting)
manifest.json – Trimble Connect extension-manifest
icon.svg      – ikon (forstørrelsesglass + vimpel)
vendor/       – lokal kopi av trimble-connect-workspace-api (IIFE-bygg)
backend/      – ifcopenshell-logikken som utfører selve IFC-endringen, kjørt lokalt (se backend/README.md)
```

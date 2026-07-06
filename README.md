# Merknader

En Trimble Connect-extension (side-panel i 3D Viewer) som lar prosjekt-admins legge til eller fjerne en **vimpel**-merknad på et valgt element, uten å gå via en lokal Flask-app og manuell filopplasting.

En vimpel er en liten IFC-geometri (grå stang + rødt flagg) plassert ved elementet, sammen med et egendefinert pset `NCC-Produksjon` (Merknad, Status, Disiplin, Prosjekt, Utført av, Revisjonsnummer, Revisjonsdato) skrevet på både vimpelen og kildeelementet.

Bygget etter samme mønster som ["Søk Armering"](https://github.com/kasterna/rebar-postliste).

## Status: Fase 1 (frontend) ferdig, Fase 2 (backend) ikke startet

Denne extensionen kan i dag:
- Koble seg til Trimble Connect og lese hvilken rolle innlogget bruker har i prosjektet (`ProjectAPI.getMembers()` + `UserAPI.getUser()`), og vise/skjule handlinger deretter.
- La en admin velge ett element i 3D-vieweren, og fylle ut en merknad i skjemaet "Legg til vimpel".
- Bygge riktig payload for både "Legg til vimpel" og "Fjern vimpel".

Den kan **ikke** ennå:
- Faktisk skrive vimpel-geometri/pset til IFC-filen eller laste opp en ny versjon til Trimble Connect. `postToBackend()` i [app.js](app.js) er en stub som logger payloaden og viser en tydelig feilstatus i stedet for å late som noe ble lagret. Dette krever en backend-tjeneste (Python/ifcopenshell) og et Trimble Connect REST API-oppsett (OAuth) som ikke er bygget eller besluttet hostet ennå — se `CLAUDE.md` for detaljer.

## Rollestyring

Ingen eget innloggingssystem. Extensionen leser gjeldende brukers rolle direkte fra Trimble Connect sin egen prosjekt-medlemsliste (`role`/`companyAdmin` per medlem). Alle andre enn admins får skrivebeskyttet visning (handlingsknappene er skjult/deaktivert, og en gul merknad forklarer hvorfor).

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

## Prosjektstruktur

```
index.html    – markup og styling
app.js        – all logikk (tilkobling, rollesjekk, valg, skjema, backend-stub)
manifest.json – Trimble Connect extension-manifest
icon.svg      – ikon (forstørrelsesglass + vimpel)
vendor/       – lokal kopi av trimble-connect-workspace-api (IIFE-bygg)
```

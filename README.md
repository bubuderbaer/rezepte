# Rezepte für den Bring!-Import

Statische Rezeptseiten mit schema.org/Recipe-Daten (JSON-LD). Der Bring!-Server liest sie über
`https://api.getbring.com/rest/bringrecipes/deeplink?url=<Seite>&source=web&baseQuantity=<P>&requestedQuantity=<N>`
und öffnet die Bring-App mit dem Import-Bildschirm. Die Buttons sitzen im Artifact „Unser Rezeptbuch“.

- `r/<rezept-id>.html` – je Rezept (Mengen = Gesamtmenge für `portionen`)
- `l/<batch>.html` – Wocheneinkauf inkl. Vorräte zum Prüfen
- `img/*.png` – Vorschaubilder für Bring
- `build_bring_pages.py <base_url> <data_dir> <out_dir>` erzeugt alles aus `data/rezepte.json` und `data/listen.json`

Seiten sind öffentlich, aber `noindex`. Sie enthalten nur Rezepte.

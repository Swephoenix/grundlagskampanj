# Utskicksmaterial for Postal och Cogworks

Den har mappen innehaller bara det som behovs for sjalva mejlet.

## Innehall

- `email-preview.html`
  - Lokal forhandsvisning. Oppna den i webblasaren for att kontrollera layout och bilder.
- `email-for-postal-cogworks.html`
  - Versionen som ska anvandas i utskicksverktyget.
  - Den innehaller platshallaren `__ASSET_BASE_URL__`.
- `assets/`
  - Alla bilder som mejlet anvander.

## Sa anvander du paketet

1. Ladda upp alla filer i `assets/` till en publik webbplats eller filyta.
2. Valj en gemensam publik bas-URL, till exempel:

```text
https://example.com/grundlagskampanj
```

3. Oppna `email-for-postal-cogworks.html`.
4. Ersatt alla forekomster av `__ASSET_BASE_URL__` med den publika bas-URL:en.
5. Klistra in den uppdaterade HTML-koden i Oderland Postal eller Cogworks utskick.

## Exempel pa bildlankar efter ersattning

```text
https://example.com/grundlagskampanj/banner.jpeg
https://example.com/grundlagskampanj/ulf-strom.jpg
https://example.com/grundlagskampanj/barbara-aberg.jpg
https://example.com/grundlagskampanj/transparent_logo.png
```

## Viktigt

- Anvand inte lokala filsokvagar i sjalva utskicksverktyget. Bilderna maste ligga publikt tillgangliga via `https://`.
- `email-preview.html` ar bara for kontroll lokalt. Den ska inte klistras in direkt i Postal eller Cogworks.
- Om verktyget erbjuder "test mail", skicka alltid ett test till flera olika inkorgar innan det riktiga utskicket.

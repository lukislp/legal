# legal

Legal texts for the apps published by Lukas Körber (GitHub: lukislp), served at
**https://legal.lktec.org**. Today these are the privacy policies of the iOS apps
MowDeck and StudyLife, in German (primary) and English.

The legal notice (Impressum) is not part of this repository; it lives at
https://lktec.org/impressum (English: https://lktec.org/en/imprint).

## Scope: who is responsible for what

MowDeck and StudyLife are self-hosted software. The texts here cover what the
publisher of the apps is responsible for: the apps as distributed through the
App Store, and the public demo instances he operates.

**Every self-hosted server installation is run by its own operator.** Whoever runs
the server a user connects to is the controller for the account and content data
stored there and must publish their own privacy policy for it. These texts do
not replace that policy. MowDeck ships a starting template for operators at
[`apps/web/static/legal/privacy.md`](https://github.com/lukislp/mowdeck/blob/main/apps/web/static/legal/privacy.md).
StudyLife does not have such a template yet; once it exists in the studylife
repository, link it from section 5 of both StudyLife policies (to do).

## Structure

Plain static HTML, served by GitHub Pages from the root of `main`
(no build step, no Jekyll: see `.nojekyll`).

| Path | Content |
| --- | --- |
| `index.html`, `en/index.html` | start page (DE, EN) |
| `<app>/index.html`, `en/<app>/index.html` | privacy policy of an app (DE, EN) |
| `assets/style.css` | the only stylesheet; light and dark via `prefers-color-scheme` |
| `scripts/check.py` | site check, run in CI on every pull request |
| `CNAME` | custom domain `legal.lktec.org` |

The pages load nothing from other hosts: no web fonts, no CDN, no analytics,
no cookies, no JavaScript.

## Changing a text

1. Branch off `main` and edit the German **and** the English page together.
   The German version is the binding one; the English one is a translation.
2. Update the "Stand" / "Last updated" date and the version number at the top
   of the page you changed.
3. Run the check locally (standard library only):

   ```sh
   python3 scripts/check.py
   ```

   It fails on a page without `lang`, title, skip link, language switch or
   footer links, on a broken internal link, on any resource loaded from
   another host, and on open-point markers (`data-todo`, `TODO`, `OFFEN:`,
   `OPEN:`). Mark anything still to be decided with such a marker: the check
   then blocks the pull request until it is resolved.
4. Open a pull request. The commit history of `main` is the public change log
   of every text (linked as "Änderungsverlauf" / "Change history" on each page).

## Licence

The texts are licensed under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
Reusing them does not make them correct for another app or service: check every
statement against what your software and your installation actually do.

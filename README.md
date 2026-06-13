# wm2026

Static GitHub Pages site for the Berlin WM 2026 public-viewing map.
It also includes a Berlin-time match timetable generated from FIFA's official
2026 World Cup schedule data.

## Deployment

GitHub Pages should serve this repository from the root of the default branch.

- Entry point: `index.html`
- Match data: `matches.json`
- Custom domain: `wm2026.artdaw.com`
- Pages domain file: `CNAME`
- Deployment workflow: `.github/workflows/deploy-pages.yml`

Match data source:
`https://www.fifa.com/de/tournaments/mens/worldcup/canadamexicousa2026/articles/spielplan-wm-2026-spiele-ergebnisse`

DNS for `wm2026.artdaw.com` must point to GitHub Pages, usually with a `CNAME`
record targeting `artdaw.github.io`.

In the repository settings, set GitHub Pages to use **GitHub Actions** as the
source. Pushes to `main` will deploy automatically.

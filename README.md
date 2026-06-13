# wm2026

Static GitHub Pages site for the Berlin WM 2026 public-viewing map.

## Deployment

GitHub Pages should serve this repository from the root of the default branch.

- Entry point: `index.html`
- Custom domain: `wm2026.artdaw.com`
- Pages domain file: `CNAME`
- Deployment workflow: `.github/workflows/deploy-pages.yml`

DNS for `wm2026.artdaw.com` must point to GitHub Pages, usually with a `CNAME`
record targeting `artdaw.github.io`.

In the repository settings, set GitHub Pages to use **GitHub Actions** as the
source. Pushes to `main` will deploy automatically.

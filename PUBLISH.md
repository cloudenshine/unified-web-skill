# Publishing Guide

How to publish `unified-web-skill` to PyPI and Docker Hub.

---

## Prerequisites

You need accounts on:
- [PyPI](https://pypi.org/) — one-time registration
- [Docker Hub](https://hub.docker.com/) — one-time registration

Install build tools:

```bash
pip install hatchling twine
```

---

## 1. PyPI

### Build

```bash
# From the project root
hatchling build
```

Output goes to `dist/` — a `.whl` and a `.tar.gz`.

### Publish

```bash
# Set your PyPI token as env var
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-xxxxxxxx..."

# Upload
twine upload dist/*
```

### Install from PyPI

```bash
pip install unified-web-skill
pip install unified-web-skill[server]    # + HTTP server mode
pip install unified-web-skill[crypto]    # + AES credential encryption
pip install unified-web-skill[video]     # + yt-dlp video extraction
pip install unified-web-skill[all]       # everything
```

---

## 2. Docker Hub

### Build

```bash
docker build -t unified-web-skill:latest .
```

### Tag & Push

```bash
docker tag unified-web-skill:latest yourdockerhub/unified-web-skill:latest
docker push yourdockerhub/unified-web-skill:latest
```

---

## 3. GitHub Actions (Automated)

The repo includes `.github/workflows/ci.yml` for tests on push.

To add automatic PyPI publishing on tag:

1. Go to GitHub → Settings → Secrets and variables → Actions
2. Add `PYPI_TOKEN` (your PyPI API token)
3. Add `DOCKER_USERNAME` and `DOCKER_TOKEN` (Docker Hub credentials)
4. Tag a release:
   ```bash
   git tag v3.1.0
   git push origin v3.1.0
   ```

Then create a `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install hatchling twine
      - run: hatchling build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}
      - run: docker build -t unified-web-skill:latest .
      - run: docker tag unified-web-skill:latest ${{ secrets.DOCKER_USERNAME }}/unified-web-skill:latest
      - run: docker push ${{ secrets.DOCKER_USERNAME }}/unified-web-skill:latest
```

---

## Version Bump

Update version in `app/__init__.py`:

```python
__version__ = "3.1.1"  # bump
```

Then rebuild and push.

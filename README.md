# pyvikunja
A python library for interfacing with a Vikunja instance

## Development

Install with [uv](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -e .
```

Run unit tests:

```bash
uv run python -m unittest discover -s tests -v
```

Live integration test against your Vikunja instance (see [scripts/README.md](scripts/README.md)):

```bash
uv run python scripts/integration_test.py
```

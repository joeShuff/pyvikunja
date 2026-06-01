# Scripts

## Integration test (live Vikunja)

Exercises label and bucket APIs against a real instance.

### Setup with [uv](https://docs.astral.sh/uv/)

From the repository root:

```bash
uv venv
uv pip install -e .
```

### Run

```bash
uv run python scripts/integration_test.py
```

You will be prompted for your Vikunja API token (hidden input). Alternatively set `VIKUNJA_TOKEN` in the environment.

### Useful flags

| Flag | Purpose |
|------|---------|
| `--discovery-only` | List projects/tasks/buckets; no writes |
| `--yes` | Skip the `yes` confirmation before mutations |
| `--no-restore` | Leave the task modified after the run |
| `--project Finances` | Project title to match |
| `--bucket Backlog` | Bucket title for the move test |
| `--base-url https://…` | Override instance URL |

### What it does

1. Finds the **Finances** project and lets you pick a task by index.
2. Runs label add/remove/bulk tests, then restores original labels.
3. Moves the task to the **Backlog** kanban bucket, then restores the original bucket if one was set.

### pip alternative

If you prefer pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python scripts/integration_test.py
```

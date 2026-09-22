# db-client

- when prompt push
  - increase patch version in pyproject.toml
  - insert {message} with version to CHANGELOG.md
  - git add .
  - git commit -m "{message}"
  - git tag vX.X.X
  - git push --tags

- when run command, use `uv` (e.g. `uv pip install`)

- when run python, use `.venv/Scripts/python.exe` with `-m` option
  (e.g. `.venv/Scripts/python.exe -m compare_schema_data.compare`)

- use `--native-tls` for pip

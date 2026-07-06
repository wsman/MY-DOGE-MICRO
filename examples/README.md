# SDK Cookbooks

These examples target a local `doged` daemon.

1. Load the cookbook environment into your shell:

```bash
cp examples/.env.example examples/.env
set -a
. examples/.env
set +a
```

2. Start the daemon:

```bash
doged serve --host 127.0.0.1 --port 8901
```

3. Install the Python SDK and run the Python cookbooks:

```bash
py -3 -m pip install -e packages/doge-sdk-python
cd examples/python
make run-01
make run-02
make run-03
make run-04
```

4. Build the TypeScript SDK, then run the TypeScript cookbooks:

```bash
cd packages/doge-sdk-typescript
npm install
npm run build

cd ../../examples/typescript
npm install
npm run run-01
npm run run-02
npm run run-03
npm run run-04
```

Environment variables:

- `DOGE_DAEMON_URL`: daemon base URL, default `http://127.0.0.1:8901`
- `DOGE_API_TOKEN`: optional bearer token for protected daemon routes
- `DOGE_SAMPLE_DOC`: document path used by upload cookbooks, default `../../README.md`

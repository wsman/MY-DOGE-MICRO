# MY-DOGE Web Console

Vue 3 + Vite console for the local MY-DOGE API.

## Development

```powershell
npm install
npm run dev
```

The dev server proxies `/api`, `/v1`, and `/health` to
`http://localhost:8901`.

## Platform Shell Flag

The workspace/project/case/template/admin shell is guarded by:

```powershell
$env:VITE_DOGE_FEATURE_PLATFORM_SHELL="1"
```

With the flag unset, the app defaults to `/research-agent` and keeps the
existing Research Agent workflow available.

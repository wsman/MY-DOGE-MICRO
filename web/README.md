# MY-DOGE Web Console

Vue 3 + Vite console for the local MY-DOGE API.

## Development

```powershell
npm install
npm run dev
```

The dev server proxies `/api`, `/v1`, and `/health` to
`http://localhost:8901`.

## Platform Shell Entry

The workspace/project/case/template/admin shell is the default local Web entry.
Opening `/` redirects to `/home`, and `/research-agent` remains directly
reachable as a compatibility route.

To roll the root route back to the legacy Research Agent entry for a local
build, set:

```powershell
$env:VITE_DOGE_FEATURE_PLATFORM_SHELL="0"
```

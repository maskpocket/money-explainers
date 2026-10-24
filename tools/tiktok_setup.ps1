# Stores the TikTok app keys inside the Cloudflare Worker (never on disk or in chat) and the shared admin key in GitHub.
$repo = "maskpocket/money-explainers"
$dir = Join-Path $PSScriptRoot "..\tiktok-worker"
function Plain($s) { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)) }
$key = Plain (Read-Host "TikTok Client key" -AsSecureString)
$sec = Plain (Read-Host "TikTok Client secret" -AsSecureString)
$admin = -join ((48..57) + (97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
Push-Location $dir
$key | npx --yes wrangler secret put TIKTOK_CLIENT_KEY
$sec | npx --yes wrangler secret put TIKTOK_CLIENT_SECRET
$admin | npx --yes wrangler secret put ADMIN_KEY
Pop-Location
$admin | gh secret set TIKTOK_ADMIN_KEY -R $repo
"https://fricomind-tiktok.antwordtech.workers.dev" | gh secret set TIKTOK_WORKER_URL -R $repo
Write-Host "Done. Keys stored."

# Exchanges a short-lived Graph API Explorer token for a non-expiring Page token
# and stores FB_PAGE_TOKEN / FB_PAGE_ID as GitHub secrets. Nothing is printed or saved to disk.
$appId = "28950144731293370"
$repo = "maskpocket/money-explainers"
$sec = Read-Host "App Secret" -AsSecureString
$tok = Read-Host "Short-lived user token from Graph API Explorer" -AsSecureString
$secret = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$short = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($tok))
$g = "https://graph.facebook.com/v21.0"
$ll = (Invoke-RestMethod "$g/oauth/access_token?grant_type=fb_exchange_token&client_id=$appId&client_secret=$secret&fb_exchange_token=$short").access_token
$pages = (Invoke-RestMethod "$g/me/accounts?access_token=$ll").data
if (-not $pages) {
  Write-Host "No Pages found. Permissions on this token:"
  (Invoke-RestMethod "$g/me/permissions?access_token=$ll").data | ForEach-Object { Write-Host ("  " + $_.permission + " = " + $_.status) }
  Write-Host ("Token user: " + (Invoke-RestMethod "$g/me?fields=name&access_token=$ll").name)
  exit 1
}
$pages | ForEach-Object { Write-Host ("Page: " + $_.name + "  id " + $_.id) }
$p = $pages | Where-Object { $_.name -like "*Fricomind*" } | Select-Object -First 1
if (-not $p) { $p = $pages[0] }
Write-Host ("Using: " + $p.name)
$p.access_token | gh secret set FB_PAGE_TOKEN -R $repo
$p.id | gh secret set FB_PAGE_ID -R $repo
$ig = (Invoke-RestMethod "$g/$($p.id)?fields=instagram_business_account&access_token=$($p.access_token)").instagram_business_account.id
if ($ig) { $ig | gh secret set IG_USER_ID -R $repo; Write-Host "Instagram account id saved." } else { Write-Host "No Instagram account linked to this Page." }
Write-Host "Done. Secrets saved."

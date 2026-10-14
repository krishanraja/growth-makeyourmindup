# The Control Center key (Krish, once, about two minutes)

The engine stores its packs in Control Center with one shared key,
`GROWTH_ENGINE_TOKEN`. The same value lives in two places: Vercel, so
Control Center accepts it, and a file on Krish's Windows PC, so the Codex
runs can send it. It never goes in this repository, a chat or a document.

## 1. Make it and save it on the PC (Windows PowerShell)

Open PowerShell and paste this one line. It works in Windows PowerShell 5.1
and in PowerShell 7, and needs nothing installed:

    $d="$HOME\.config\growth-makeyourmindup"; New-Item -ItemType Directory -Force -Path $d | Out-Null; $b=New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); $k=-join($b|ForEach-Object{$_.ToString('x2')}); [IO.File]::WriteAllText("$d\token",$k); icacls "$d\token" /inheritance:r /grant:r "$($env:USERNAME):F" | Out-Null; Set-Clipboard -Value $k; Write-Host "saved, and copied"

It prints `saved, and copied`. The key is now in
`C:\Users\<you>\.config\growth-makeyourmindup\token`, readable only by your
Windows account, and on your clipboard.

## 2. Put it in Vercel

1. Open https://vercel.com/krish-rajas-projects/control-center/settings/environment-variables
2. Under "Add Environment Variable":
   - Key: `GROWTH_ENGINE_TOKEN`
   - Value: paste (Ctrl+V)
   - Environments: **Production** only (untick Preview and Development)
   - Sensitive: on
3. Press **Save**.
4. Open https://vercel.com/krish-rajas-projects/control-center/deployments,
   then the top Production deployment, then the "..." menu, then
   **Redeploy**. Confirm, and wait until it says Ready (about two minutes).

## 3. Check it (PowerShell)

    $k=(Get-Content "$HOME\.config\growth-makeyourmindup\token" -Raw).Trim(); Invoke-RestMethod "https://controlcenter.krishraja.com/api/growth/packs?days=1" -Headers @{Authorization="Bearer $k"}

It should print `ok : True`.
- An error naming **401**: the two values differ. Run
  `Get-Content "$HOME\.config\growth-makeyourmindup\token" | Set-Clipboard`
  and paste that into Vercel again (step 2).
- An error naming **503**: the redeploy has not finished yet, or was missed.

## If you ever need a new key

Run step 1 again (it overwrites the file), then step 2 with the new value.
The old key stops working as soon as the redeploy is Ready.

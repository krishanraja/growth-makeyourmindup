# The Control Center key (Krish, once, about two minutes)

The engine stores its packs in Control Center with one shared key,
`GROWTH_ENGINE_TOKEN`. The same value lives in two places: Vercel (so
Control Center accepts it) and a file on your Mac (so the Codex runs send
it). It never goes in this repository, a chat or a document.

## 1. Make it and save it on your Mac

Open Terminal and paste this one line:

    mkdir -p ~/.config/growth-makeyourmindup && openssl rand -hex 32 | tee ~/.config/growth-makeyourmindup/token | tr -d '\n' | pbcopy && chmod 600 ~/.config/growth-makeyourmindup/token && echo "saved, and copied"

It prints "saved, and copied". The key is now in the file and on your
clipboard.

## 2. Put it in Vercel

1. Open https://vercel.com/krish-rajas-projects/control-center/settings/environment-variables
2. Under "Add Environment Variable":
   - Key: `GROWTH_ENGINE_TOKEN`
   - Value: paste (Cmd+V)
   - Environments: **Production** only (untick Preview and Development)
   - Sensitive: on
3. Press **Save**.
4. Open https://vercel.com/krish-rajas-projects/control-center/deployments,
   then the top Production deployment, then the "..." menu, then
   **Redeploy**. Confirm. Wait until it says Ready, about two minutes.

## 3. Check it

In Terminal, from your clone of this repository:

    python3 growth.py doctor

Every line should say `ready`. If "Control Center accepts the key" says 401,
the two values differ: repeat step 2 with the file's value
(`pbcopy < ~/.config/growth-makeyourmindup/token`). If it says 503, the
redeploy has not finished or was missed.

## If you ever need a new key

Run step 1 again (it overwrites the file), then step 2 with the new value.
The old key stops working as soon as the redeploy is Ready.

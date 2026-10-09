# Canyon Diagnostic Agent: Setup Guide (Version 0.1)

This guide puts the app online in about 20 minutes. No coding needed. You only click, drag files and paste text.

## What is in this folder

* `app.py`: the web app screens
* `diag_engine.py`: the master data checks and scoring
* `ai_summary.py`: writes the executive summary with Claude (switched on later)
* `requirements.txt`: the list of tools the host installs automatically
* `sample_material_master.csv`: illustrative sample data, not client data
* `.streamlit/config.toml`: Canyon colors (optional, a hidden folder)

## Step 1: Create a GitHub account (5 minutes)

GitHub is where the app's files are stored online.

1. Go to github.com and click **Sign up**. Use your Canyon email.
2. Verify your email.

## Step 2: Upload the app files (5 minutes)

1. On GitHub, click the **+** at the top right, then **New repository**.
2. Name it `canyon-diagnostic-agent`. Choose **Private**. Click **Create repository**.
3. On the next page, click the link **uploading an existing file**.
4. Unzip the folder on your computer. Drag all the files inside it into the browser window.
   * The `.streamlit` folder is hidden on most computers. If it does not upload, that is fine. The app works without it, only the colors change.
5. Click **Commit changes**.

## Step 3: Put the app online (5 minutes)

We use Streamlit Community Cloud, which is free for this stage.

1. Go to share.streamlit.io and click **Continue with GitHub**. Allow access.
2. Click **Create app**, then **Deploy a public app from GitHub** (we lock it with a password in Step 4).
3. Repository: `your-github-name/canyon-diagnostic-agent`. Branch: `main`. Main file path: `app.py`.
4. Optional: choose a short web address, for example `canyon-diagnostic`.
5. Click **Deploy**. Wait two to three minutes while it installs.

## Step 4: Lock it with a password (2 minutes)

1. On your app page, click **Manage app** (bottom right), then the three dots, then **Settings**, then **Secrets**.
2. Paste this line, with your own password:

```
APP_PASSWORD = "choose-a-strong-password"
```

3. Click **Save**. The app restarts and now asks for the password.

## Step 5: Test it

1. Open the app and sign in.
2. Type a client name in the left panel, for example "Demo Client".
3. Click **Use illustrative sample**. You should see 37 records, a score of 67 out of 100 and 12 duplicate clusters.
4. Click **Excel report** and open the file. It has four sheets: Summary, Findings, Duplicate Clusters, All Records.

## Important: client data rule for this stage

Until Canyon's Tech Lead has reviewed the app, use it only with:

* the illustrative sample, or
* real client files where the client has agreed in writing to a pilot.

For production with many clients, we will move the app to Canyon's own Azure or AWS (Amazon Web Services) account in an Indian region.

## Later: switch on the AI (Artificial Intelligence) summary

1. Create an account at console.anthropic.com, add billing, and create an API (Application Programming Interface) key.
2. Copy the current model name from Anthropic's models page in the docs.
3. In the app's **Secrets**, add:

```
ANTHROPIC_API_KEY = "paste-your-key"
CLAUDE_MODEL = "paste-the-model-name"
```

4. The **Executive summary** tab now has a **Write executive summary** button. Only the totals and a few example records are sent to the AI, never the whole file.

Never share the API key in email, chat or screenshots.

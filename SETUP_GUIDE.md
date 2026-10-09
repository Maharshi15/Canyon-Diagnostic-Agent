# Canyon Diagnostic Agent: Setup Guide (Version 0.4)

This guide puts the app online in about 20 minutes. No coding needed. You only click, drag files and paste text.

## What is in this folder

* `app.py`: the web app screens
* `diag_engine.py`: the master data checks and scoring
* `ai_summary.py`: writes the executive summary with Azure OpenAI or Claude
* `requirements.txt`: the list of tools the host installs automatically
* `app_engine.py`: the Application Diagnostic review and analytics checks
* `module_application.py`: the Application Diagnostic screen
* `process_engine.py` and `module_process.py`: the Process Diagnostic checks and screen
* `report_engine.py` and `module_report.py`: the client Diagnostic Report (Word)
* `module_pilot.py`: the Pilot Request Kit (message to pilot clients and data request checklist)
* `samples/`: illustrative sample data, screenshots of a fictional app and a fictional process, not client data
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

## Switch on the AI (Artificial Intelligence) summary with Azure OpenAI

You need three values from your Azure OpenAI resource.

1. Sign in to portal.azure.com and open your Azure OpenAI resource.
2. Open **Keys and Endpoint**. Copy the **Endpoint** and **KEY 1**.
3. Open Azure AI Foundry from the resource and go to **Deployments**. Copy the **deployment name** exactly as written. It is the name your team gave the deployment, which may differ from the model name.
4. In the app's **Secrets**, keep your password line and add:

```
AZURE_OPENAI_ENDPOINT = "https://your-resource-name.openai.azure.com/"
AZURE_OPENAI_API_KEY = "paste-key-1-here"
AZURE_OPENAI_DEPLOYMENT = "paste-deployment-name-here"
```

5. Click **Save**. The **Executive summary** tab now shows "AI provider: Azure OpenAI" and a **Write executive summary** button.

If you get an "unauthorized" or "not found" error, add one more line and save again:

```
AZURE_OPENAI_API_VERSION = "2024-10-21"
```

Only the totals and a few example records are sent to the AI, never the whole file.

Never share the key in email, chat or screenshots.

(The app can also use Anthropic Claude instead: add ANTHROPIC_API_KEY and CLAUDE_MODEL. If both are set, Azure OpenAI is used.)

## Application Diagnostic (version 0.3)

1. In the left panel, choose **Application Diagnostic**.
2. Click **Use illustrative sample** to see a full example without using the AI.
3. For a real review: fill in the application name and journey, then upload screenshots of one journey in order. Name the files 01, 02, 03 so the order is kept.
4. Optional: upload a funnel export (columns: step, users; first row is users who started, then one row per screen with users who completed it) and a page usage export (columns: page, views). These turn findings into measured evidence.
5. Click **Run application diagnostic**. It takes up to a minute. Then download the Excel report.

Your Azure deployment must accept images (for example a GPT 4o, GPT 4.1 or GPT 5 deployment). Hide personal data in screenshots before uploading.

## Process Diagnostic (version 0.4)

1. In the left panel, choose **Process Diagnostic**.
2. Open the **Illustrative sample** tab and click **Use illustrative sample**, then **Run process diagnostic**. You should see 10 steps, 6 findings, a cycle time of 10 days and 1,436 manual hours a month.
3. For a real process, use one of the other two tabs:
   * **Upload a step table**: an Excel or CSV file with the columns Step, Owner, System, Type, Work minutes, Wait hours, and optionally Share of cases %. Type is one of Task, Data entry, Check, Approval, Handoff.
   * **Draft from an SOP with AI**: upload the SOP (Word, PDF or text) or paste the description. The AI drafts the table. It never invents times, so add them yourself with the process owner.
4. Check and edit the step table on screen, enter **Cases per month**, and choose where the times come from (estimates are Evidence level 1, system timestamps are level 2).
5. Click **Run process diagnostic**. The tabs show findings, a process map, automation opportunities ranked by impact, and pilot experiments. Download the Excel report.

All counts, times and ratings are calculated by the app. The AI is only used to draft the step table from a document.

## Diagnostic Report (version 0.4)

1. Run one or more modules first (samples work too). Results stay available while the browser tab is open.
2. Choose **Diagnostic Report**. Tick the modules to include, check the **Prepared by** and **Contact** fields, and pick **Full report** or **One page summary for a prospect**.
3. Check the preview, then click **Download Word report**. To send a PDF, open it in Word and use File, Save As, PDF.

Reports built from sample data carry a red "Illustrative" line on the cover. Read every finding before sending.

## Pilot Request Kit (version 0.4)

1. Choose **Pilot Request Kit**. Enter the contact's first name, the company, what the pilot covers, and one real detail about them.
2. Copy the LinkedIn message, the email or the follow up with the copy icon on each box.
3. Click **Download checklist (Word)** and attach it to the email. It lists what to share per module, how Canyon handles the data, and a short pilot confirmation the client signs or replies with.

Tick **Say the pilot is at no cost** only when Canyon has agreed to that. Confirm the data handling lines with the Canyon Tech Lead until the security review is done.

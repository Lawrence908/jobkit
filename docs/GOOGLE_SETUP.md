# Google OAuth, Drive & Sheets setup

This guide walks through configuring the `.env` variables for Google OAuth (lines 21–25) and Drive/Sheets (lines 27–32).

---

## Part 1: OAuth client (`.env` lines 21–25)

### 1. Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one (e.g. “JobKit”).
3. Note the project; you’ll use it for both OAuth and APIs.

### 2. Enable APIs

1. In the left menu: **APIs & Services** → **Enabled APIs & services**.
2. Click **+ Enable APIs and Services**.
3. Enable:
   - **Google Drive API**
   - **Google Sheets API**

### 3. Configure the OAuth consent screen

1. **APIs & Services** → **OAuth consent screen**.
2. Choose **External** (unless you use a Google Workspace org and want Internal).
3. Fill in:
   - **App name**: e.g. `JobKit`
   - **User support email**: your email
   - **Developer contact**: your email
4. Click **Save and Continue**.
5. **Scopes**: Add scopes (or add them when creating the client):
   - `https://www.googleapis.com/auth/drive.file` (see and manage Drive files created by this app)
   - `https://www.googleapis.com/auth/spreadsheets` (see, edit, create, delete Sheets)
6. **Test users** (if app is in “Testing”): Add your Google account so you can sign in.
7. Save and continue through the summary.

### 4. Create OAuth 2.0 Client ID

1. **APIs & Services** → **Credentials**.
2. **+ Create Credentials** → **OAuth client ID**.
3. **Application type**: **Web application**.
4. **Name**: e.g. `JobKit web`.
5. **Authorized redirect URIs** → **+ Add URI**:
   - Production: `https://jobs.chrislawrence.ca/api/google/oauth/callback`
   - If you use a different app URL, set that here and in `GOOGLE_OAUTH_REDIRECT_URI` in `.env`.
6. Click **Create**.
7. Copy the **Client ID** and **Client secret** and put them in `.env`:

```env
GOOGLE_OAUTH_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret_here
GOOGLE_OAUTH_REDIRECT_URI=https://jobs.chrislawrence.ca/api/google/oauth/callback
```

### 5. Token encryption key

The app encrypts the Google refresh token in the database. Generate a 32-byte base64 key and set it once (changing it later invalidates existing stored tokens):

```bash
python3 -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Put the output in `.env`:

```env
GOOGLE_TOKEN_ENCRYPTION_KEY=that_base64_string_here
```

### 6. Connect in the app

1. Restart the backend so it loads the new env vars.
2. Log in to JobKit (username/password).
3. In the header, click **Connect Google** (or open `/api/google/oauth/start` in the same browser where you’re logged in).
4. Approve the requested Drive and Sheets access.
5. You’ll be redirected back; the header should show **Google: Connected**.

---

## Part 2: Drive & Sheets (`.env` lines 27–32)

### Drive: `GOOGLE_DRIVE_ROOT_FOLDER_ID`

JobKit uploads resume PDFs and other artifacts into a folder per job. You can either:

- **Leave it empty**: The app will create a folder named **JobKit** in your Drive root and use it as the root for all job folders.
- **Use an existing folder**: Put that folder’s ID here so all job folders are created inside it.

**How to get a folder ID**

1. In Google Drive, create or open the folder you want as root (e.g. “JobKit”).
2. Open the folder and look at the URL:
   - `https://drive.google.com/drive/folders/`**`1ABC...xyz`**
3. The part after `/folders/` is the folder ID. Put it in `.env`:

```env
GOOGLE_DRIVE_ROOT_FOLDER_ID=1ABC...xyz
```

(Leave the line empty or omit it to auto-create “JobKit” at the root.)

---

### Sheets: `GOOGLE_SHEETS_SPREADSHEET_ID`

**How to get the spreadsheet ID**

1. Create a new Google Sheet or open the one you want to use as the job tracker.
2. Look at the URL:
   - `https://docs.google.com/spreadsheets/d/`**`1ABC...xyz`**`/edit...`
3. The long string between `/d/` and `/edit` is the spreadsheet ID:

```env
GOOGLE_SHEETS_SPREADSHEET_ID=1ABC...xyz
```

---

### Sheets: `GOOGLE_SHEETS_TAB_NAME`

The sheet is made of tabs (e.g. “Sheet1”, “Job Applications”). Use the **exact** tab name as shown in the tab bar (case-sensitive):

```env
GOOGLE_SHEETS_TAB_NAME=Job Applications
```

If your tab is named “Sheet1”, use `GOOGLE_SHEETS_TAB_NAME=Sheet1`.

---

### Sheets: `GOOGLE_SHEETS_URL_COLUMN`

JobKit finds or adds a row by matching the **Job URL** in a column. That column’s header must match this value (case-insensitive):

```env
GOOGLE_SHEETS_URL_COLUMN=Job URL
```

---

### Sheets: optional column mapping (your headers)

If your sheet has **different column names or order**, set the optional env vars so JobKit writes to the right columns. JobKit will only update the columns you map; others (e.g. Salary, Rejection Reason, or future email/response columns) are left as-is when updating a row.

Example for a sheet with headers:

**Company Name · Job URL · Application Status · Role · Salary · Date Submitted · Link to Job Req · Rejection Reason · Resume Used · Notes**

Add to `.env`:

```env
GOOGLE_SHEETS_URL_COLUMN=Job URL
GOOGLE_SHEETS_COLUMN_COMPANY=Company Name
GOOGLE_SHEETS_COLUMN_ROLE=Role
GOOGLE_SHEETS_COLUMN_STATUS=Application Status
GOOGLE_SHEETS_COLUMN_JOB_URL=Job URL
GOOGLE_SHEETS_COLUMN_LINK_TO_JOB_REQ=Link to Job Req
GOOGLE_SHEETS_COLUMN_DATE_SUBMITTED=Date Submitted
GOOGLE_SHEETS_COLUMN_RESUME_LINK=Resume Used
GOOGLE_SHEETS_COLUMN_NOTES_LINK=Notes
```

- **Link to Job Req** gets the same URL as Job URL; set `GOOGLE_SHEETS_COLUMN_LINK_TO_JOB_REQ=Link to Job Req` so both columns are filled.
- **Salary** and **Rejection Reason** have no mapping; leave them blank in the config and fill them manually (or later via email integration).
- **Cover letter** link: if you add a column for it, set `GOOGLE_SHEETS_COLUMN_COVER_LINK=Your Column Name`.

All mapping is case-insensitive. If you don’t set any `GOOGLE_SHEETS_COLUMN_*` vars, JobKit uses the default column order (see table below).

**Default columns** (when no mapping is set):

| Column (example) | Purpose |
|------------------|--------|
| Timestamp        | When the row was added/updated |
| Company          | Company name |
| Role             | Job title |
| **Job URL**      | Used to match rows |
| Status           | e.g. Applied, Interviewing |
| Resume link      | Drive link to resume PDF |
| Cover letter link | Drive link to cover letter |
| Notes link       | Drive link to notes |
| Keywords         | Extracted keywords |
| Location         | Job location |
| Source           | Where the job was found |
| Updated          | Last update time |

---

## Summary: `.env` snippet

After setup, your Google-related block might look like:

```env
# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=123456789-xxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxx
GOOGLE_OAUTH_REDIRECT_URI=https://jobs.chrislawrence.ca/api/google/oauth/callback
GOOGLE_TOKEN_ENCRYPTION_KEY=your_32_byte_base64_key

# Drive/Sheets
GOOGLE_DRIVE_ROOT_FOLDER_ID=1ABC...xyz
GOOGLE_SHEETS_SPREADSHEET_ID=1ABC...xyz
GOOGLE_SHEETS_TAB_NAME=Job Applications
GOOGLE_SHEETS_URL_COLUMN=Job URL
# Optional: match your sheet headers (see docs)
# GOOGLE_SHEETS_COLUMN_COMPANY=Company Name
# GOOGLE_SHEETS_COLUMN_STATUS=Application Status
# ...
```

OAuth is required for “Connect Google” and for Upload + Log. Drive and Sheets IDs are only needed if you use **Upload to Drive + Log to Sheets**; without them, Drive upload may still work (using the auto-created JobKit folder), but Sheets logging will not. Email/response tracking can be added later; Salary and Rejection Reason stay as manual columns until then.

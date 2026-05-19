# Sharing this demo with a recruiter (PBIX + email)

## Produce a single PBIX file

1. Regenerate the project (optional but recommended so paths and data match your machine). For a **smaller PBIX** (fewer time-entry rows), use **`--interview`** on the generator (or run smoke after generating with that flag):

   ```powershell
   cd legal_bi_pbip_kit
   py scripts\generate_legal_bi_pbip.py --interview
   ```

   Or the usual full dataset + checks:

   ```powershell
   py scripts\smoke_pbip.py
   ```

2. Open **`output\Sidley_BI_Modernization_Demo\Sidley_BI_Modernization_Demo.pbip`** in **Power BI Desktop** (current channel with PBIP / Fabric Git integration support).

3. Wait for **Refresh** to finish (CSV mode uses the bundled `data\*.csv` under that folder).

4. **File → Save As** (or **Save a copy**) and choose **Power BI report files (\*.pbix)**.  
   Use a clear filename, e.g. `YourName_Sidley_BI_Modernization_Demo.pbix`.

5. Attach that **PBIX** to your email (or upload to the link the recruiter sent). If the attachment is too large, zip the PBIX or use your firm’s approved file transfer.

**Note:** The semantic model stores **absolute paths** to the CSV folder at generation time. After **Save As PBIX**, the dataset is embedded; the recruiter does **not** need your repo or network path. If you stay in PBIP mode and move folders, re-run the generator before opening again.

**Theme in PBIX:** The kit registers **Sidley Com** in `report.json` + `StaticResources/RegisteredResources/SidleyCom.json`. If Desktop still opens on the default palette after **Save As**, use **View → Themes → Sidley Com** once, then save again (some Desktop builds only embed the **currently selected** theme). Regenerate with the latest generator so `themeCollection` includes a proper `reportVersionAtImport` object (required for Fabric / PBIX).

---

## Suggested email (copy and personalize)

**Subject:** Portfolio sample — Power BI modernization demo (PBIX attached)

**Body:**

Hello [Name],

Thank you again for coordinating the process for the [Senior Business Intelligence Engineer / title] opportunity. For context ahead of [phone screen / panel / hiring manager conversation], I am attaching a **Power BI sample** I prepared that lines up with the role’s emphasis on **enterprise reporting, semantic modeling, and modernization** from legacy BI into Power BI.

**What you are receiving**

- A **single PBIX** built in Power BI Desktop: an **eight-page** executive-style report (KPIs, trends, matter and migration views, stakeholder backlog, refresh health, an RLS demo page, and a small “visual lab” page) backed by a **star-schema import model** with **centralized DAX measures**, a **time-intelligence calculation group**, **hierarchies**, and **sample RLS roles**.

- The dataset is **synthetic / demo-only** (no client matter data); it is meant to show how I structure **certified reusable measures**, **slicer sync**, and **documentation-friendly** project layout rather than to represent any real firm.

**How to open it**

- Install **Power BI Desktop** (current release). Double-click the PBIX, allow **data refresh** when prompted. No database or cloud sign-in is required for the default **CSV** mode packaged in the file.

If it would help the hiring team, I can also supply the underlying **PBIP** source tree (Git-friendly project format) and a short **talk track** document that maps each page to typical Sidley stakeholders and modernization themes.

Best regards,  
[Your name]  
[Phone — optional]  
[LinkedIn or portfolio — optional]

---

## One-line summary for a forwarding note

“Attached: self-contained Power BI Desktop sample (PBIX) — 8-page report, star schema, DAX + calculation group + RLS demo, synthetic data — for the Sidley BI engineer conversation.”

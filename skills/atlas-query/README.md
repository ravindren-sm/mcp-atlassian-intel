# atlas-query — Claude Code Skill

A Claude Code skill for querying Intel's **Atlas product lifecycle data** via Snowflake (ECA) or iBI DaaS REST API.

Once installed, Claude automatically uses this skill whenever you ask about Atlas products, milestone dates, POR/Trend/Actual schedules, or product planning data.

---

## AGS Access Requirements

Request all roles at `goto/ags` → Submit Request for Self.

| Entitlement | Approver | Required For |
| --- | --- | --- |
| `cda_design_product_planning_prod_reader` | DFlowAnalytics | Snowflake / ECA path (primary) |
| `IPG iBI Data Read Access` | Auto-approved | iBI DaaS API login |
| `IPG iBI Cloud Read` | Auto-approved | iBI Cloud access |
| `EC GER ibi_idc_5961 R` | Approver-idc.10311 | iBI DaaS Atlas views (fallback) |

**Minimum to get started:** `cda_design_product_planning_prod_reader` alone unlocks the Snowflake path, which covers all Atlas milestone and properties data.

**After approval:** Run `klist purge` in a Command Prompt to refresh your Kerberos ticket before first use.

---

## Quick Install

Paste this prompt into Claude Code and it will do everything:

```
Set up the atlas-query skill on my machine.

1. Install the required Python packages via the Intel proxy:
   pip install snowflake-connector-python requests requests-kerberos --proxy="http://proxy-chain.intel.com:911"

2. Create the skill directory and download the skill file:
   mkdir -p ~/.claude/skills/atlas-query
   curl -L -o ~/.claude/skills/atlas-query/SKILL.md https://raw.githubusercontent.com/ravindren-sm/mcp-atlassian-intel/main/skills/atlas-query/SKILL.md

3. Confirm the skill loaded by listing skills — atlas-query should appear.

My Intel email: <paste your firstname.lastname@intel.com here>
```

---

## Manual Install

### Step 1 — Install Python packages

```cmd
pip install snowflake-connector-python requests requests-kerberos --proxy="http://proxy-chain.intel.com:911"
```

### Step 2 — Copy the skill file

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills\atlas-query"
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/ravindren-sm/mcp-atlassian-intel/main/skills/atlas-query/SKILL.md" `
  -OutFile "$env:USERPROFILE\.claude\skills\atlas-query\SKILL.md" `
  -Proxy "http://proxy-chain.intel.com:911"
```

### Step 3 — Update the skill with your email

Open `%USERPROFILE%\.claude\skills\atlas-query\SKILL.md` and replace `firstname.lastname@intel.com` with your actual Intel email address (used for Snowflake SSO).

### Step 4 — Verify

Restart Claude Code. The skill is active when you see `atlas-query` in the skills list, or when Claude automatically queries Atlas data in response to product milestone questions.

---

## What It Does

Once installed, just ask Claude naturally:

```
What are the upcoming milestones for Nova Lake H?
```
```
Show me the POR and Trend dates for Arrow Lake S PRQ.
```
```
Find all products with NOVA in the name and show their stepping schedule.
```

Claude will write and run the Snowflake query, display results, and fall back to iBI DaaS automatically if Snowflake is unavailable.

---

## Access Modes

### Snowflake / ECA (Primary)

- **Server:** `xd14286-ecdw.privatelink.snowflakecomputing.com`
- **Auth:** Browser SSO (Azure AD) — a login window opens on first query each session
- **Database:** `PRODUCT_ENGINEERING.DESIGN_PRODUCT_PLANNING_ANALYSIS`
- **Key view:** `PRODUCT_ENGINEERING_SCHEDULE` — milestone dates with POR, Trend, Actual, Drive-To

### iBI DaaS REST API (Fallback)

- **URL:** `https://ibi-daas.intel.com/daas/web/services/sql`
- **Auth:** Windows Kerberos SSO — automatic, no login window needed
- **Key views:** `V_RAWDATA_ATLAS_PRODUCT_MILESTONES`, `V_RAWDATA_ATLAS_PRODUCT_PROPERTIES`, `V_BM_AIM_ATLAS_CALCULATED_DATES`

---

## Troubleshooting

**iBI returns "access denied"**
Run `klist purge` in Command Prompt, wait 10–15 minutes (AD replication), then try again. Role must be fully provisioned and replicated.

**Snowflake SSO opens browser but fails with "user mismatch"**
The SSO popup may default to a personal Microsoft account. Click your `firstname.lastname@intel.com` account explicitly.

**`pip install` fails with SSL error**
Add `--proxy="http://proxy-chain.intel.com:911"` to the pip command.

**Skill not appearing after install**
Restart Claude Code — skills are loaded at session start.

# mcp-atlassian — Intel Internal Edition

Fork of [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian) with a patch
for Intel's corporate proxy environment. Provides Claude Code with native read/write access
to Intel's internal Confluence wiki and Jira.

## What's Different from Upstream

Intel's corporate proxy (`proxy-chain.intel.com:911`) intercepts outbound HTTPS. The standard
`mcp-atlassian` server ignores the `NO_PROXY` environment variable when proxies are explicitly
configured on the session, causing all requests to internal hosts to be routed through the proxy
and fail.

This fork patches `src/mcp_atlassian/utils/ssl.py` to add:

- **`NoProxyAdapter`** — an `HTTPAdapter` that correctly respects `NO_PROXY` even when the
  session has explicit proxy settings
- **`configure_proxy_bypass()`** — mounts the adapter for a given service URL
- **`SSLIgnoreAdapter`** now inherits from `NoProxyAdapter`, so SSL bypass and proxy bypass
  work together

---

## Prerequisites

- Python 3.10+
- `uv` package manager: `pip install uv` (provides `uvx` and `uv tool install`)
- Git
- Access to `wiki.ith.intel.com` (requires Intel network or VPN)

---

## Authentication Setup

### Confluence Personal Access Token (PAT)

This tool uses a **Personal Access Token**, not your regular Confluence password.
PATs are long-lived API credentials that don't expire with SSO.

1. Go to **https://wiki.ith.intel.com**
2. Click your profile icon (top right) → **Profile**
3. Click **Personal Access Tokens** → **Create Token**
4. Give it a name (e.g. `Claude Code MCP`)
5. Copy the token — you won't see it again

> Store it securely. Do not commit it to any repository.

### Jira Personal Access Token (optional)

For Jira access (`jira.devtools.intel.com`):

1. Go to **https://jira.devtools.intel.com**
2. Profile → **Personal Access Tokens** → **Create Token**

---

## Installation

```bash
# Clone this repo
git clone https://github.com/ravindren-sm/mcp-atlassian-intel.git
cd mcp-atlassian-intel

# Install as a persistent uv tool (fast startup — no per-session install overhead)
uv tool install --from . mcp-atlassian
```

Verify installation:

```bash
mcp-atlassian --help
```

---

## Running the Server

Run in **HTTP mode** (recommended) so Claude Code connects instantly without Python cold-start delay:

```bash
# Set your credentials
set CONFLUENCE_URL=https://wiki.ith.intel.com
set CONFLUENCE_PERSONAL_TOKEN=<your-confluence-pat>
set CONFLUENCE_SSL_VERIFY=false
set JIRA_URL=https://jira.devtools.intel.com
set JIRA_PERSONAL_TOKEN=<your-jira-pat>
set JIRA_AUTH_TYPE=bearer
set JIRA_SSL_VERIFY=false
set NO_PROXY=.devtools.intel.com,wiki.ith.intel.com

# Start server
mcp-atlassian --transport streamable-http --port 8765
```

Health check:
```bash
curl http://localhost:8765/healthz
# Expected: {"status":"ok"}
```

---

## Claude Code Integration

Register the server once (user-scoped, available in all projects):

```bash
claude mcp add -s user --transport http atlassian-mcp http://localhost:8765/mcp
```

Verify:

```bash
claude mcp list
# Expected: atlassian-mcp: http://localhost:8765/mcp (HTTP) - ✓ Connected
```

---

## Auto-Start at Windows Logon (Task Scheduler)

Create a VBScript launcher that sets credentials and starts the server silently:

**`start-atlassian-mcp.vbs`** (do not commit — contains credentials):

```vbs
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

WshShell.Environment("Process")("CONFLUENCE_URL") = "https://wiki.ith.intel.com"
WshShell.Environment("Process")("CONFLUENCE_PERSONAL_TOKEN") = "<your-pat>"
WshShell.Environment("Process")("CONFLUENCE_SSL_VERIFY") = "false"
WshShell.Environment("Process")("JIRA_URL") = "https://jira.devtools.intel.com"
WshShell.Environment("Process")("JIRA_SSL_VERIFY") = "false"
WshShell.Environment("Process")("NO_PROXY") = ".devtools.intel.com,wiki.ith.intel.com"

' 0 = hidden window, False = don't wait for exit
WshShell.Run """C:\Users\<username>\.local\bin\mcp-atlassian.exe"" --transport streamable-http --port 8765", 0, False

Set WshShell = Nothing
```

Register as a scheduled task (PowerShell):

```powershell
$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument 'C:\Users\<username>\start-atlassian-mcp.vbs'
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'Atlassian MCP Server' -Action $action -Trigger $trigger -Settings $settings -Force
```

Replace `<username>` and `<your-pat>` with your values.

---

## Example Claude Prompts

Once connected, you can talk to Claude naturally:

```
Search Confluence for pages about "NVL binning strategy"
Get the content of Confluence page with ID 3167956975
Find all pages in the ITSpdxtp space modified in the last 7 days
List child pages of page ID 3167956975
Add a comment to page ID 4545578836 saying "Updated with latest findings"
```

---

## Troubleshooting

**`✗ Failed to connect` in `claude mcp list`**
The server isn't running. Run the VBScript or start the server manually, then check `curl http://localhost:8765/healthz`.

**`401 Unauthorized`**
Your PAT has expired. Create a new one in Confluence/Jira.

**`Failed to resolve 'wiki.ith.intel.com'`**
You're not on Intel network or VPN.

**SSL errors**
Ensure `CONFLUENCE_SSL_VERIFY=false` is set. Intel's network does SSL inspection.

---

## Updating from Upstream

```bash
git stash          # stash the Intel patch
git pull origin main
git stash pop      # re-apply patch
# If conflicts, manually re-apply src/mcp_atlassian/utils/ssl.py changes
```

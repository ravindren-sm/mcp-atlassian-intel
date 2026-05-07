# mcp-atlassian — Intel Internal Edition

Fork of [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian) with a patch
for Intel's corporate proxy environment. Gives Claude Code native access to
**wiki.ith.intel.com** — search, read, create, and update wiki pages directly from Claude.

## What's Different from Upstream

Intel's corporate proxy (`proxy-chain.intel.com:911`) intercepts outbound HTTPS. The standard
`mcp-atlassian` server ignores the `NO_PROXY` environment variable when proxies are explicitly
configured on the session, routing internal traffic through the proxy and failing.

This fork patches `src/mcp_atlassian/utils/ssl.py` to add:

- **`NoProxyAdapter`** — respects `NO_PROXY` even when proxies are explicitly set on the session
- **`configure_proxy_bypass()`** — mounts the adapter for a given service URL
- **`SSLIgnoreAdapter`** now inherits from `NoProxyAdapter` so SSL bypass and proxy bypass work together

---

## Prerequisites

- **Python 3.10+** — verify with `python --version`
- **Git** — verify with `git --version`
- **Claude Code CLI** — install from [https://docs.anthropic.com/en/docs/claude-code/getting-started](https://docs.anthropic.com/en/docs/claude-code/getting-started), verify with `claude --version`
- Intel network or VPN access to `wiki.ith.intel.com`

---

## Step 1 — Get an Intel Confluence Personal Access Token

The MCP server authenticates with a **Personal Access Token (PAT)**, not your SSO password.
PATs are long-lived API keys that survive SSO session expiry.

1. Log into **[https://wiki.ith.intel.com](https://wiki.ith.intel.com)**
2. Click your **profile picture** (top-right corner)
3. Select **Profile** from the dropdown
4. Click **Settings**
5. Click **Personal Access Tokens** (left sidebar)
6. Click the **Create Token** button
7. Give it a descriptive name, e.g. `Claude Code MCP`
8. Leave the expiry as-is (or set one if required by your org policy)
9. Click **Create** and **copy the token immediately** — it will not be shown again

> Keep this token private. Do not commit it to any file or repository.

---

## Step 2 — Install the Server

**Install `uv`** (the package manager used to install and run the server):

```bash
pip install uv --proxy="http://proxy-chain.intel.com:911"
```

**Configure git to use the Intel proxy** (required for cloning from GitHub on corporate network):

```bash
git config --global http.proxy http://proxy-chain.intel.com:911
```

**Clone and install:**

```bash
git clone https://github.com/ravindren-sm/mcp-atlassian-intel.git
cd mcp-atlassian-intel
uv tool install --from . mcp-atlassian
```

> First install downloads ~120 packages and takes 1-2 minutes.

**Find the installed executable path** — you'll need this in Step 3:

```bash
where mcp-atlassian
# Example output: C:\Users\ravindre\.local\bin\mcp-atlassian.exe
```

---

## Step 3 — Create the Startup Script

Create a file called **`start-atlassian-mcp.vbs`** in your home directory
(`C:\Users\<your-username>\start-atlassian-mcp.vbs`).

**Do not commit this file — it contains your PAT.**

```vbs
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

' Set credentials only for this process — not system-wide
WshShell.Environment("Process")("CONFLUENCE_URL") = "https://wiki.ith.intel.com"
WshShell.Environment("Process")("CONFLUENCE_PERSONAL_TOKEN") = "<paste-your-pat-here>"
WshShell.Environment("Process")("CONFLUENCE_SSL_VERIFY") = "false"
WshShell.Environment("Process")("NO_PROXY") = "wiki.ith.intel.com"

' Replace the path below with the output of: where mcp-atlassian
' Launch the server silently on port 8765 (0 = hidden window, False = don't wait)
WshShell.Run """C:\Users\<your-username>\.local\bin\mcp-atlassian.exe"" --transport streamable-http --port 8765", 0, False

Set WshShell = Nothing
```

Replace `<paste-your-pat-here>` and the exe path with your actual values from `where mcp-atlassian`.

---

## Step 4 — Register for Auto-Start at Logon

Open **PowerShell** (search "PowerShell" in the Windows Start menu) and run:

```powershell
$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "C:\Users\$env:USERNAME\start-atlassian-mcp.vbs"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'Atlassian MCP Server' -Action $action -Trigger $trigger -Settings $settings -Force
```

The server will start silently in the background on every Windows logon.

To start it manually without logging off:

```
wscript.exe C:\Users\<your-username>\start-atlassian-mcp.vbs
```

Health check (wait ~10 seconds after running the VBScript):

```bash
curl http://localhost:8765/healthz
# Expected: {"status":"ok"}
```

---

## Step 5 — Connect Claude Code

The server must be running (healthz returns `ok`) before running this.

Run once to register the server (user-scoped, applies to all projects):

```bash
claude mcp add -s user --transport http atlassian-mcp http://localhost:8765/mcp
```

Verify:

```bash
claude mcp list
# Expected: atlassian-mcp: http://localhost:8765/mcp (HTTP) - ✓ Connected
```

---

## Troubleshooting

**`✗ Failed to connect` in `claude mcp list`**
The server is not running. Run the VBScript or check Task Scheduler. Then verify with
`curl http://localhost:8765/healthz`.

**`401 Unauthorized`**
Your PAT has expired or is wrong. Create a new one at wiki.ith.intel.com → Profile → Settings →
Personal Access Tokens → Create Token. Update the VBScript with the new token.

**`Failed to resolve 'wiki.ith.intel.com'`**
You are not on Intel network or VPN.

**SSL certificate errors**
Ensure `CONFLUENCE_SSL_VERIFY=false` is set in the VBScript. Intel's network performs SSL
inspection with an internal CA that Python does not trust by default.

**`git clone` fails with proxy error**
Run `git config --global http.proxy http://proxy-chain.intel.com:911` and retry.

---

## Updating from Upstream

```bash
cd mcp-atlassian-intel
git stash           # stash Intel patch changes
git pull origin main
git stash pop       # re-apply
# If ssl.py has conflicts, re-apply the changes from intel_noproxy.patch manually
uv tool install --from . mcp-atlassian  # reinstall with updated code
```

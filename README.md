# Knossos — remote LAN filesystem + CLI access over MCP

> The Minoan palace whose labyrinth guarded the center. The **server machine** is the
> labyrinth; this MCP server is the thread of Ariadne that leads an AI agent to its
> files and CLI — from another machine on the same network.

Knossos is a small **MCP server (Streamable HTTP)** that runs on one Windows machine
(the **server**, e.g. a powerful box that runs your local models) and exposes its
**filesystem** and **command-line** to an MCP client running on **another machine**
(the **client**, e.g. your daily-driver laptop) over the **LAN** — authenticated and
restricted.

- **Transport:** Streamable HTTP (`/mcp`), stateless, JSON responses.
- **Auth:** Bearer token in a header, validated by middleware (constant-time compare).
- **Safety:** directory allowlist (anti path-traversal), binary allowlist, command
  timeout, never `shell=True`.

---

> ## ⚠️ Security — read before running
>
> Knossos exposes **file read/write and arbitrary command execution** of the server
> machine over the network. That is powerful and, if misconfigured, dangerous. Only run
> it on a **trusted LAN**, and always:
>
> - Use a **strong random token** (`KNOSSOS_TOKEN`), kept out of any repository.
> - Keep the **directory allowlist** (`KNOSSOS_ALLOWED_DIRS`) as small as possible.
> - Keep the **binary allowlist** (`KNOSSOS_ALLOWED_BINS`) specific. Allowing a general
>   shell (`powershell`, `cmd`, `bash`) effectively allows *any* program, because a shell
>   can spawn other programs — so the allowlist stops being a real boundary.
> - Lock the port to the **client's IP** with a firewall rule (`scripts/setup-firewall.ps1`).
> - **Never** port-forward this port on your router. Knossos is **LAN-only**.
>
> No transport encryption is used by default (plain HTTP on the LAN). For stronger
> setups, see *Future work* below.

---

## Tools

| Tool | What it does |
|---|---|
| `health` | version, hostname, time, active allowlist — connection test |
| `system_info` | OS, CPU, RAM, GPU (via `nvidia-smi`) |
| `list_dir` | list a directory inside the allowlist |
| `read_file` | read a file (text or base64), with a byte cap |
| `write_file` | write/append, creating parent dirs inside the allowlist |
| `stat_path` | metadata for a path |
| `run_command` | run argv (list or string) with restricted cwd, timeout, bin allowlist |
| `delete_path` | delete a file/empty dir — **only if `KNOSSOS_ALLOW_DELETE=true`**, needs `confirm=true` |

## Choosing what to expose (access control)

Knossos gives you three independent dials to decide exactly how much of the server
machine an authenticated client can touch. Tighten or loosen each to taste — start
restrictive and open only what you actually need.

**1. Which folders — `KNOSSOS_ALLOWED_DIRS`** (the strongest boundary).
Every file tool (`list_dir`, `read_file`, `write_file`, `stat_path`, `delete_path`) and
the working directory of `run_command` are confined to these roots. Anything outside is
rejected, and `..`/symlink escapes are resolved away. This is the boundary that actually
contains the agent — keep the list as small as the task allows.
- *Read-only-ish exposure:* point it at a single project or models folder.
- *Broad exposure:* add more roots; each one is fully readable **and writable**.

**2. Which programs — `KNOSSOS_ALLOWED_BINS`** (a convenience filter, **not** a sandbox).
`run_command` will only launch an executable whose name is on this list. Important caveats
so you choose deliberately:
- The match is by **name, not path** — `python` allows `C:\anywhere\python.exe`, not a
  specific binary.
- Some "binaries" are effectively a general shell. **`powershell`, `cmd`, `bash` — and
  also `python` (`python -c "..."`) — can launch any other program.** Putting any of
  these on the list means `run_command` can run essentially anything, so the bin allowlist
  stops being a real restriction. That may be exactly what you want (full automation) or
  exactly what you don't (least privilege). Decide on purpose.
- Leaving the list **empty allows any binary** (the server prints a warning at startup).
- *Most restrictive useful setup:* list only the specific tools you'll call, none of which
  is a shell or interpreter (e.g. `nvidia-smi;ollama`).
- *Full-power setup:* add `powershell` (or `python`) and accept that the client can run
  anything within the allowed directories.

**3. Whether deletion is possible — `KNOSSOS_ALLOW_DELETE`** (off by default).
The `delete_path` tool isn't even registered unless this is `true`, and even then it only
removes a single file or an *empty* directory and requires `confirm=true`. Leave it `false`
unless you specifically need remote deletion.

**The real security perimeter is the token + the firewall rule**, not the bin allowlist.
Any client holding `KNOSSOS_TOKEN` is trusted by design and — if a shell/interpreter is
allowed — can run arbitrary code within the allowed directories. So: guard the token,
restrict the port to the client's IP (`scripts/setup-firewall.ps1`), and treat the
allowlists as how much you *delegate* to that already-trusted client.

## Requirements

- **Server machine:** Windows, Python 3.10+. (Optional: [NSSM](https://nssm.cc) to run as a service.)
- **Client machine:** an MCP client (e.g. Claude Desktop) with **Node.js / `npx`** available
  (used by the `mcp-remote` bridge — see *Client setup*).

## Server setup (the machine being accessed)

1. **Clone and configure:**
   ```powershell
   git clone https://github.com/legalworkshop/knossos_mcp.git
   cd knossos_mcp
   copy .env.example .env
   # generate a strong token:
   python -c "import secrets;print(secrets.token_urlsafe(48))"
   ```
   Edit `.env`:
   - `KNOSSOS_TOKEN` = the generated token (never commit it).
   - `KNOSSOS_ALLOWED_DIRS` = allowed root folders, `;`-separated (e.g. `D:\models;D:\projects`).
   - `KNOSSOS_ALLOWED_BINS` = allowed executables (e.g. `python;ollama;whisper;nvidia-smi`).

2. **Run:** double-click **`start-knossos.bat`**, or:
   ```powershell
   .\scripts\run.ps1
   ```
   First run creates the venv (`.venv`), installs the package, and serves on
   `http://0.0.0.0:8765/mcp`. While the `.bat` window is open the machine **won't sleep
   from inactivity** (via `SetThreadExecutionState`); closing the window releases that.

   > **Laptop:** keep-awake prevents idle sleep but does **not** override **closing the
   > lid**. To keep the server awake on lid-close (while plugged in), in an elevated
   > PowerShell:
   > ```powershell
   > powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
   > powercfg /setactive SCHEME_CURRENT
   > ```

3. **Start on login (optional):**
   ```powershell
   .\scripts\add-to-startup.ps1          # add (undo with -Remove)
   ```
   Or run as a boot service via `scripts\install_service.ps1` (NSSM, elevated shell).

4. **Lock the firewall to the client's IP** (elevated PowerShell):
   ```powershell
   .\scripts\setup-firewall.ps1 -ClientIp <CLIENT_IP>
   ```
   Find IPs with `ipconfig`. Ideally reserve the server's IP via DHCP on your router.

5. **Smoke test** (server running, in another terminal):
   ```powershell
   .\.venv\Scripts\python.exe scripts\smoke_test.py
   ```
   Checks: `health` with the token, a bad token rejected (401), and a path outside the
   allowlist refused.

## Client setup (the machine running the agent)

Most MCP clients (including **Claude Desktop**) only launch **stdio** servers from their
config — they do **not** accept a remote HTTP URL directly. Bridge to Knossos with
[`mcp-remote`](https://www.npmjs.com/package/mcp-remote), which speaks stdio to the client
and Streamable HTTP to the server.

Install it once on the client:
```powershell
npm install -g mcp-remote
```

Then add Knossos to the client config (for Claude Desktop:
`%APPDATA%\Claude\claude_desktop_config.json`). Using `npx`:

```json
{
  "mcpServers": {
    "knossos": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "http://<SERVER_IP>:8765/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer <KNOSSOS_TOKEN>"
      ]
    }
  }
}
```

- `--allow-http` is required because this is plain HTTP on the LAN (not HTTPS).
- `<KNOSSOS_TOKEN>` must match the server's `.env`. Treat this config file as a secret.

> **Windows note:** if `npx` fails to launch (e.g. a "`'C:\Program' is not recognized`"
> error from a space in the Node path), call `node` directly on the installed script:
> ```json
> "command": "C:\\Program Files\\nodejs\\node.exe",
> "args": ["<npm-root-g>\\mcp-remote\\dist\\proxy.js", "http://<SERVER_IP>:8765/mcp",
>          "--allow-http", "--header", "Authorization: Bearer <KNOSSOS_TOKEN>"]
> ```
> Find `<npm-root-g>` with `npm root -g`.

Restart the client, then call the `health` tool to confirm the bridge works.

## Environment variables

| Var | Default | Description |
|---|---|---|
| `KNOSSOS_TOKEN` | — | **required.** Bearer token. |
| `KNOSSOS_HOST` | `0.0.0.0` | listen interface. |
| `KNOSSOS_PORT` | `8765` | TCP port. |
| `KNOSSOS_ALLOWED_DIRS` | — | **required.** Allowed roots, `;`-separated. |
| `KNOSSOS_ALLOWED_BINS` | empty | allowed binaries; empty = any (not recommended). |
| `KNOSSOS_CMD_TIMEOUT` | `300` | max seconds per command. |
| `KNOSSOS_MAX_READ_BYTES` | `5000000` | default `read_file` cap. |
| `KNOSSOS_ALLOW_DELETE` | `false` | enable the `delete_path` tool. |

## Security checklist

- [ ] Token ≥ 32 bytes, kept out of any repo (`.env` is gitignored).
- [ ] Directory allowlist minimal and tested (path traversal blocked).
- [ ] Binary allowlist specific (no general shell unless you accept the trade-off).
- [ ] Command timeout configured.
- [ ] Firewall rule restricting the port to the client's IP.
- [ ] No router port-forwarding.
- [ ] `health` works with the token and is rejected (401) without it.

## Future work

- SSH tunnel (OpenSSH on Windows) + bind to `127.0.0.1` for transport encryption.
- Native TLS (self-signed cert on the LAN).
- Streaming for long-running jobs (`run_command_stream`).
- Per-call audit logs (who, when, which tool, which path/command).

## License

MIT — see [LICENSE](LICENSE).

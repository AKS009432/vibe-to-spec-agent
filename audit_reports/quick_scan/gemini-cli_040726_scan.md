# Quick Scan Findings: Gemini CLI

## Summary
The `gemini-cli` is a powerful terminal-based interface for interacting with Gemini models, offering extensive features like file system access, shell command execution, and MCP support. While these features provide high utility, they introduce significant security surfaces that require careful management.

## Findings

### CRITICAL: Arbitrary Shell Command Execution
- **What it is:** The CLI allows the model to execute shell commands on the user's machine.
- **What it means:** If the AI model is prompted or tricked into executing malicious code, it has the permissions of the current terminal user.
- **Real-world exploit scenario:** An attacker crafts a malicious `GEMINI.md` or a remote context file that, when parsed by the CLI, triggers a shell command to exfiltrate sensitive environment variables (e.g., `AWS_SECRET_ACCESS_KEY`) or install a backdoor.
- **Affected location:** Documentation indicates usage of "Shell Commands" tool (referencing `https://www.geminicli.com/docs/tools/shell`).

### HIGH: Excessive File System Access
- **What it is:** The tool has built-in file operations capability.
- **What it means:** The CLI can read, write, and modify files in directories it has access to, including sensitive config files or private keys.
- **Real-world exploit scenario:** A user runs the CLI in their home directory. A compromised project context or a malicious prompt causes the agent to overwrite `.ssh/authorized_keys` or read sensitive configuration files in `~/.config`.
- **Affected location:** Documentation references "File System Operations" (referencing `https://www.geminicli.com/docs/tools/file-system`).

### MEDIUM: MCP Server Exposure
- **What it is:** The CLI supports Model Context Protocol (MCP) servers.
- **What it means:** MCP servers extend the agent's capabilities. If an improperly secured or untrusted MCP server is added, it becomes a vector for command injection or unauthorized data access.
- **Real-world exploit scenario:** A user adds a third-party, unverified MCP server to `~/.gemini/settings.json`. The server is designed to scrape user project code and send it to an attacker-controlled endpoint.
- **Affected location:** Documentation references `~/.gemini/settings.json` (referencing `https://www.geminicli.com/docs/tools/mcp-server`).

### LOW: Over-reliance on "Trusted Folders" for Security
- **What it is:** The security model relies on "Trusted Folders".
- **What it means:** Users might mistakenly assume that any folder not marked "trusted" is completely safe, potentially leading to complacency when running the CLI in sensitive directories.
- **Real-world exploit scenario:** A user trusts their `~/work` directory but runs a quick query in a `~/temp` directory, assuming standard agent behavior, unaware that shell execution might still be enabled or configured globally.
- **Affected location:** Documentation references "Trusted Folders" (referencing `https://www.geminicli.com/docs/cli/trusted-folders`).

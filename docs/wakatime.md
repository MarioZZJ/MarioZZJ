# WakaTime setup

The profile workflow reads two aggregated values for the last 30 days: coding time and total AI tokens. Coding time comes from editor plugins. AI tokens require the WakaTime integration for each AI agent; installing only the VS Code extension does not cover separate Codex CLI or Claude Code sessions.

Use the same WakaTime account and API key on every machine. Never commit the key to this repository.

## 1. Store the API key on each machine

Get the key from the [WakaTime API Key page](https://wakatime.com/api-key), then create the shared WakaTime configuration file.

macOS and Linux:

```text
~/.wakatime.cfg
```

Windows:

```text
%USERPROFILE%\.wakatime.cfg
```

The file must contain:

```ini
[settings]
api_key = waka_your_key_here
```

For remote development, the file must exist on the remote machine too. A local key is not automatically forwarded to a VS Code Remote SSH extension host.

## 2. Install the agent integrations where the agents run

### Codex

Run these commands once on every machine where Codex is used:

```shell
codex plugin marketplace add wakatime/codex-cli-wakatime
codex plugin add codex-cli-wakatime@wakatime
```

Start a new Codex session after installation. In the Codex desktop app, open **Plugins → Installed** and verify that the WakaTime plugin is enabled before starting a new task.

Official instructions: [WakaTime for Codex CLI](https://wakatime.com/codex-cli).

### Claude Code

Run these commands once on every machine where Claude Code is used:

```shell
claude plugin marketplace add https://github.com/wakatime/claude-code-wakatime.git
claude plugin install claude-code-wakatime@wakatime
```

Start a new Claude Code session after installation.

Official instructions: [WakaTime for Claude Code](https://wakatime.com/claude-code).

### VS Code and Remote SSH

Install the editor extension locally:

```shell
code --install-extension WakaTime.vscode-wakatime
```

For a Remote SSH workspace, open the Extensions panel after connecting and choose **Install in SSH: _host_** for WakaTime. This records editor time on that remote machine; install the Codex or Claude integration separately if the agent itself runs there.

Official instructions: [WakaTime for VS Code](https://wakatime.com/vs-code).

## 3. Verify telemetry before trusting the profile number

1. Start a new agent session and make a small real edit.
2. Open the [WakaTime plugin status page](https://wakatime.com/settings/plugins).
3. Confirm that `Codex CLI` or `Claude Code`, the expected operating system, and a recent `last seen` time appear.
4. Open the WakaTime AI dashboard and confirm that input and output token counts are increasing.
5. Manually run the repository's **Refresh profile** workflow and verify that it changes only the two marked README blocks.

The GitHub repository also needs one Actions secret named `WAKATIME_TOKEN`, containing the same API key. Set it through **Settings → Secrets and variables → Actions**; do not place the key in workflow YAML, README content, command history, or a committed file.

## Privacy

WakaTime receives file paths, project names, activity metadata, and AI token metadata, but not file contents. If project or file names are sensitive, use WakaTime's `hide_project_folder`, `hide_project_names`, `hide_file_names`, or `exclude` settings before enabling a new machine.

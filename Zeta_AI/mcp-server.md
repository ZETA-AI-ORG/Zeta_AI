# Render MCP Server

Render's **Model Context Protocol** (**MCP**) server enables you to manage your Render infrastructure directly from compatible AI apps, such as Cursor and Claude Code:

<video playsinline autoplay loop muted controls width="700">
  <source src="../assets/images/docs/mcp-listusers.mp4"/>
</video>

Using natural language prompts, you can:

- Spin up new services
- Query your databases
- Analyze metrics and logs

...and more! For inspiration, see some [example prompts.](#example-prompts)

<details>

<summary><strong>What is MCP?</strong></summary>

[**Model Context Protocol**](https://modelcontextprotocol.io/introduction) (**MCP**) is an open standard for connecting AI applications to external tools and data. An **MCP server** exposes a set of actions that AI apps can invoke to help fulfill relevant user prompts (e.g., "Find all the documents I edited yesterday").

To perform an action, an MCP server often calls an external API, then packages the result into a standardized format for the calling application.

</details>

## How it works

The Render MCP server is hosted at the following URL:

```
https://mcp.render.com/mcp
```

You can configure compatible AI apps (such as [Cursor](https://docs.cursor.com/context/mcp) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp)) to communicate with this server. When you provide a relevant prompt, your tool intelligently calls the MCP server to execute supported platform actions:



<img src="#" alt="Diagram of using the hosted Render MCP server with Cursor" />



**In the example diagram above:**

1. A user prompts Cursor to "List my Render services".
2. Cursor intelligently detects that the Render MCP server supports actions relevant to the prompt.
3. Cursor directs the MCP server to execute the `list_services` "[tool](https://modelcontextprotocol.io/docs/concepts/tools)", which calls the Render API to fetch the corresponding data.

<generic-block>

To explore the implementation of the MCP server itself, see the open-source project:

<button-link href="https://github.com/render-oss/render-mcp-server" target="_blank">View source on GitHub</button-link>

</generic-block>

## Setup

### 1. Create an API key

The MCP server uses an [API key](/docs/api#1-create-an-api-key) to authenticate with the Render platform. Create an API key from your [Account Settings page](https://dashboard.render.com/settings#api-keys):



<img src="#" alt="Creating an API key in the Render Dashboard" />



<warning-block>

**Render API keys are broadly scoped.** They grant access to all workspaces and services your account can access.

Before proceeding, make sure you're comfortable granting these permissions to your AI app. The Render MCP server currently supports only one potentially destructive operation: modifying an existing service's environment variables.

</warning-block>

### 2. Configure your tool

Next, we'll configure your AI app to use Render's hosted MCP server. Most compatible apps define their MCP configuration in a JSON file (such as `~/.cursor/mcp.json` for Cursor).

Select the tab for your app:

<tab-switcher>

<tab-switcher-item label="Cursor">

#### Cursor setup

Add the following configuration to `~/.cursor/mcp.json`:

```json{3-8}
{
  "mcpServers": {
    "render": {
      "url": "https://mcp.render.com/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_API_KEY>"
      }
    }
  }
}
```

Replace `<YOUR_API_KEY>` with your [API key](#1-create-an-api-key).

For more details, see the [Cursor MCP documentation](https://docs.cursor.com/en/context/mcp#using-mcp-json).

</tab-switcher-item>

<tab-switcher-item label="Claude Code">

#### Claude Code setup

Run the following command, substituting your [API key](#1-create-an-api-key) where indicated:

```bash
claude mcp add --transport http render https://mcp.render.com/mcp --header "Authorization: Bearer <YOUR_API_KEY>"
```

You can include the `--scope` flag to specify where this MCP configuration is stored. For more details, see the [Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp#option-3%3A-add-a-remote-http-server).

</tab-switcher-item>

<tab-switcher-item label="Claude Desktop">

#### Claude Desktop setup

Add the configuration below to your Claude Desktop MCP settings. By default, this file is located at the following paths based on your operating system:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json{3-14}
{
  "mcpServers": {
    "render": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.render.com/mcp",
        "--header",
        "Authorization: Bearer ${RENDER_API_KEY}"
      ],
      "env": {
        "RENDER_API_KEY": "<YOUR_API_KEY>"
      }
    }
  }
}
```

Replace `<YOUR_API_KEY>` with your [API key](#1-create-an-api-key).

For more details, see the [Claude Desktop MCP documentation](https://modelcontextprotocol.io/quickstart/user).

</tab-switcher-item>

<tab-switcher-item label="Windsurf">

#### Windsurf setup

Add the following configuration to `~/.codeium/windsurf/mcp_config.json`:

```json{3-8}
{
  "mcpServers": {
    "render": {
      "url": "https://mcp.render.com/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_API_KEY>"
      }
    }
  }
}
```

Replace `<YOUR_API_KEY>` with your [API key](#1-create-an-api-key).

For more details, see the [Windsurf MCP documentation](https://docs.windsurf.com/windsurf/cascade/mcp#mcp-config-json).

</tab-switcher-item>

<tab-switcher-item label="Other tools">

#### Setup for other apps

See the documentation for other popular AI apps:

- [VS Code](https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp)
- [Zed](https://zed.dev/docs/ai/mcp)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md)
- [Crush](https://github.com/charmbracelet/crush#mcps)
- [Warp](https://docs.warp.dev/knowledge-and-collaboration/mcp#adding-an-mcp-server)

</tab-switcher-item>

</tab-switcher>

### 3. Set your workspace

To start using the Render MCP server, you first tell your AI app which Render workspace to operate in. This determines which resources the MCP server can access.

You can set your workspace with a prompt like `Set my Render workspace to [WORKSPACE_NAME]`.



<img src="#" alt="Selecting an active Render workspace in Cursor" />



If you _don't_ set your workspace, your app usually directs you to specify one if you submit a prompt that uses the MCP server (such as `List my Render services`):



<img src="#" alt="Selecting an active Render workspace in Cursor" />



With your workspace set, you're ready to start prompting! Get started with some [example prompts](#example-prompts).

## Example prompts

Your AI app can use the Render MCP server to perform a wide variety of platform actions. Here are some basic example prompts to get you started:

#### Service creation

<blockquote>Create a new database named user-db with 5 GB storage</blockquote>

<blockquote>Deploy an example Flask web service on Render using https://github.com/render-examples/flask-hello-world</blockquote>

#### Data analysis

<blockquote>Using my Render database, tell me which items were the most frequently bought together</blockquote>

<blockquote>Query my read replica for daily signup counts for the last 30 days</blockquote>

#### Service metrics

<blockquote>What was the busiest traffic day for my service this month?</blockquote>

<blockquote>What did my service's autoscaling behavior look like yesterday?</blockquote>

#### Troubleshooting

<blockquote>Pull the most recent error-level logs for my API service</blockquote>

<blockquote>Why isn't my site at example.onrender.com working?</blockquote>

## Supported actions

The Render MCP server provides a "[tool](https://modelcontextprotocol.io/docs/concepts/tools)" for each platform action listed below (organized by resource type). Your AI app (the "MCP host") can combine these tools however it needs to perform the tasks you describe.

<info-block>

For more details on all available tools, see the [project README](https://github.com/render-oss/render-mcp-server).

</info-block>

<table>
<thead>
<tr>
<th>Resource Type</th>
<th>Supported Actions</th>
</tr>
</thead>
<tbody>
<tr>
<td>

**Workspaces**

</td>
<td>

- List all workspaces you have access to
- Set the current workspace
- Fetch details of the currently selected workspace

</td>
</tr>
<tr>
<td>

**Services**

</td>
<td>

- Create a new web service or static site
  - Other service types are not yet supported.
- List all services in the current workspace
- Retrieve details about a specific service
- Update all environment variables for a service

</td>
</tr>
<tr>
<td>

**Deploys**

</td>
<td>

- List the deploy history for a service
- Get details about a specific deploy

</td>
</tr>
<tr>
<td>

**Logs**

</td>
<td>

- List logs matching provided filters
- List all values for a given log label

</td>
</tr>
<tr>
<td>

**Metrics**

</td>
<td>

- Fetch performance metrics for services and datastores, including:
  - CPU / memory usage
  - Instance count
  - Datastore connection counts
  - Web service response counts, segmentable by status code
  - Web service response times (requires a **Professional** workspace or higher)
  - Outbound bandwidth usage

</td>
</tr>
<tr>
<td>

**Render Postgres**

</td>
<td>

- Create a new database
- List all databases in the current workspace
- Get details about a specific database
- Run a read-only SQL query against a specific database

</td>
</tr>
<tr>
<td>

**Render Key Value**

</td>
<td>

- List all Key Value instances in your Render account
- Get details about a specific Key Value instance
- Create a new Key Value instance

</td>
</tr>
</tbody>
</table>

## Running locally

<info-block>

**We strongly recommend using Render's [hosted MCP server](#2-configure-your-tool) instead of running it locally.**

The hosted MCP server automatically updates with new capabilities as they're added. Run locally only if required for your use case.

</info-block>

You can install and run the Render MCP server on your local machine as a Docker container, or by running the executable directly:

<tab-switcher>

<tab-switcher-item label="Docker image">

#### Docker setup

<info-block>

**This method requires `docker`.**

</info-block>

With this configuration, your AI app pulls and runs the Render MCP server as a Docker container.

Add JSON with the format below to your tool's MCP configuration (substitute `<YOUR_API_KEY>` with your [API key](/docs/api#1-create-an-api-key)):

```json{3-18}
{
  "mcpServers": {
    "render": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "RENDER_API_KEY",
        "-v",
        "render-mcp-server-config:/config",
        "ghcr.io/render-oss/render-mcp-server"
      ],
      "env": {
        "RENDER_API_KEY": "<YOUR_API_KEY>"
      }
    }
  }
}
```

The `mcpServers` key above might differ for specific tools. For example, Zed uses `context_servers` and GitHub Copilot uses `servers`. Consult your tool's documentation for details.

</tab-switcher-item>

<tab-switcher-item label="Executable">

#### Local executable setup

With this configuration, your AI app runs the Render MCP server executable directly.

1. Install the MCP server executable using one of the methods described in [Local installation](#local-installation), then return here.

2. Add JSON with the format below to your tool's MCP configuration (substitute your [API key](/docs/api#1-create-an-api-key) and the path to your MCP server executable):

   ```json{3-8}
   {
     "mcpServers": {
       "render": {
         "command": "/path/to/render-mcp-server-executable",
         "env": {
           "RENDER_API_KEY": "<YOUR_API_KEY>"
         }
       }
     }
   }
   ```

   The `mcpServers` key above might differ for specific tools. For example, Zed uses `context_servers` and GitHub Copilot uses `servers`. Consult your tool's documentation for details.

</tab-switcher-item>

</tab-switcher>

### Local installation

<info-block>

**Follow these instructions only if you're running the MCP server [locally](#running-locally) and without Docker.**

We strongly recommend instead using Render's hosted MCP server, because it automatically updates as new capabilities are added.

</info-block>

<details>

<summary><strong>View installation methods</strong></summary>

<tab-switcher>

<tab-switcher-item label="Install script">

<info-block>

**This method requires macOS or Linux.**

</info-block>

1. Run the following `curl` command:

   ```shell
   curl -fsSL https://raw.githubusercontent.com/render-oss/render-mcp-server/refs/heads/main/bin/install.sh | sh
   ```

2. Note the full path where the install script saved the downloaded executable. The output includes a message like the following:

   ```
   ✨ Successfully installed Render MCP Server to /Users/example/.local/bin/render-mcp-server
   ```

</tab-switcher-item>

<tab-switcher-item label="Direct download">

1. Open the MCP server's [GitHub releases page.](https://github.com/render-oss/render-mcp-server/releases)

2. Under the most recent release, download and unzip the executable that corresponds to your system's architecture.

   - If a release asset isn't available for your architecture, select a different installation method.

3. Move the executable to the desired directory and note its full path.

<info-block>

**Note for macOS users:**

You might need to grant a system exception to run the downloaded executable, because it's from an "unknown developer." [Learn more.](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac)

</info-block>

</tab-switcher-item>

<tab-switcher-item label="Build from source">

<info-block>

**We recommend building from source only in the following cases:**

- No other installation method works for your system.
- You're making custom changes to the MCP server.

</info-block>

1. Install the [Go programming language](https://go.dev/doc/install) if you haven't already.

2. Clone the MCP server repository and build the executable:

   ```shell
   git clone https://github.com/render-oss/render-mcp-server.git
   cd render-mcp-server
   go build
   ```

   This creates a `render-mcp-server` executable in the repo's root directory.

3. Note the full path to the newly built executable.

</tab-switcher-item>

</tab-switcher>

</details>

## Limitations

The Render MCP server attempts to minimize exposing sensitive information (like connection strings) to your AI app's context. However, Render does not _guarantee_ that sensitive information will not be exposed. Exercise caution when interacting with secrets in your AI app.

Note the following additional limitations:

- The MCP server supports creation of the following resources:

  - [Web services](/docs/web-services)
  - [Static sites](/docs/static-sites)
  - [Render Postgres databases](/docs/postgresql)
  - [Render Key Value instances](/docs/key-value)

  Other service types (private services, background workers, and cron jobs) are not yet supported.

- The MCP server does not support creating [free instances](/docs/free).

- The MCP server does not support all configuration options when creating services.

  - For example, you cannot create image-backed services or set up IP allowlists. If there are options you'd like to see supported, please submit an issue on the MCP server's [GitHub repository](https://github.com/render-oss/render-mcp-server/issues).

- The MCP server does not support modifying or deleting existing Render resources, with one exception:

  - You _can_ modify an existing service's environment variables.
  - To perform other modifications or deletions, use the [Render Dashboard](https://dashboard.render.com) or [REST API](/docs/api).

- The MCP server does not support triggering deploys, modifying scaling settings, or other operational service controls.
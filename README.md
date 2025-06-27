# MCP Server for Fider

A Model Context Protocol (MCP) server that provides tools to interact with [Fider](https://getfider.com/) - an open-source customer feedback tool.

## Features

This MCP server provides the following tools:

- **list_posts** - List posts with filtering options (search, view, limit, tags)
- **get_post** - Retrieve a specific post by number
- **create_post** - Create new posts (requires authentication)
- **edit_post** - Edit existing posts (requires collaborator/admin role)
- **delete_post** - Delete posts (requires admin role)
- **respond_to_post** - Change post status (open, planned, started, completed, declined, duplicate)

## Installation

### Using uvx (recommended - no installation needed!)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run directly from PyPI (once published)
uvx --from mcp-fider==2025.06.27.160000 --refresh-package mcp-fider mcp-fider

# Or run from GitHub directly
uvx --from git+https://github.com/ringostat/fider-mcp.git mcp-fider
```

### Using pip (if you prefer traditional method)

```bash
# Clone the repository
git clone https://github.com/ringostat/fider-mcp.git
cd fider-mcp

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Configuration

The server requires the following environment variables:

- `FIDER_BASE_URL` or `FIDER_URL` - Your Fider instance URL (e.g., `https://feedback.example.com`)
- `FIDER_API_KEY` - Optional API key for authentication (required for creating, editing, and deleting posts)

### Getting a Fider API Key

1. Log in to your Fider instance as an administrator
2. Go to Settings → API
3. Generate a new API key
4. Copy the key and set it as the `FIDER_API_KEY` environment variable

## Usage

### With Claude Desktop

1. Add the server to your Claude Desktop configuration file:

   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   
   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the following configuration:

```json
{
  "mcpServers": {
    "fider": {
      "command": "uvx",
      "args": ["--from", "mcp-fider==2025.06.27.160000", 
               "--refresh-package", "mcp-fider", "mcp-fider"],
      "env": {
        "FIDER_BASE_URL": "https://your-fider-instance.com",
        "FIDER_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

3. Restart Claude Desktop

### Running Directly

You can also run the server directly for testing:

```bash
# Set environment variables
export FIDER_BASE_URL="https://your-fider-instance.com"
export FIDER_API_KEY="your-api-key-here"

# Run from PyPI (once published)
uvx --from mcp-fider==2025.06.27.160000 --refresh-package mcp-fider mcp-fider

# Or run from GitHub directly
uvx --from git+https://github.com/ringostat/fider-mcp.git mcp-fider
```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black .
uv run ruff check .
```

### Publishing to PyPI

```bash
# Build the package
uv build

# Publish to PyPI
uv publish
```

## Tool Descriptions

### list_posts

List posts from Fider with optional filtering.

Parameters:
- `query` (string) - Search keywords
- `view` (string) - Filter and order options: all, recent, my-votes, most-wanted, most-discussed, planned, started, completed, declined, trending
- `limit` (integer) - Number of entries to return (1-100, default: 30)
- `tags` (string) - Comma-separated list of tags to filter by

### get_post

Get a specific post by its number.

Parameters:
- `number` (integer, required) - The post number to retrieve

### create_post

Create a new post (requires authentication).

Parameters:
- `title` (string, required) - The title of the post
- `description` (string) - The description of the post

### edit_post

Edit an existing post (requires collaborator/admin role).

Parameters:
- `number` (integer, required) - The post number to edit
- `title` (string, required) - The new title of the post
- `description` (string) - The new description of the post

### delete_post

Delete a post (requires admin role).

Parameters:
- `number` (integer, required) - The post number to delete
- `reason` (string) - Reason for deletion

### respond_to_post

Respond to a post by changing its status (requires collaborator/admin role).

Parameters:
- `number` (integer, required) - The post number to respond to
- `status` (string, required) - The new status: open, planned, started, completed, declined, duplicate
- `text` (string) - Optional description of the status change
- `originalNumber` (integer) - Required when status is 'duplicate' - the post number to merge into

## Troubleshooting

### Connection Issues

- Ensure your Fider instance is accessible from your network
- Check that the `FIDER_BASE_URL` is correct and doesn't have a trailing slash
- Verify your API key is valid if you're getting authentication errors

### Permission Errors

- Creating, editing, and deleting posts requires proper authentication
- Ensure your API key has the necessary permissions for the operations you're trying to perform

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
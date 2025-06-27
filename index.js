const readline = require('readline');
const https = require('https');
const http = require('http');
const { URL } = require('url');

console.error("Fider MCP server started (readline based).");

// Configuration - these should be set via environment variables
const FIDER_BASE_URL = process.env.FIDER_BASE_URL || process.env.FIDER_URL || 'https://your-fider-instance.com';
const FIDER_API_KEY = process.env.FIDER_API_KEY || '';

// Remove trailing slash if present
const baseUrl = FIDER_BASE_URL.replace(/\/$/, '');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

function sendResponse(id, result) {
  const response = {
    jsonrpc: '2.0',
    id: id,
    result: result,
  };
  const message = JSON.stringify(response);
  console.log(message); // Use console.log for stdout
  console.error(`Sent response for ID ${id}: ${message}`);
}

function sendError(id, code, message, data = null) {
  const response = {
    jsonrpc: '2.0',
    id: id,
    error: {
      code: code,
      message: message,
      data: data
    }
  };
  const errorMessage = JSON.stringify(response);
  console.log(errorMessage); // Use console.log for stdout
  console.error(`Sent error for ID ${id}: ${errorMessage}`);
}

// Helper function to make HTTP requests
function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const isHttps = urlObj.protocol === 'https:';
    const httpModule = isHttps ? https : http;
    
    const requestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port || (isHttps ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Fider-MCP-Server/1.0.0',
        ...options.headers
      }
    };

    // Add API key if available
    if (FIDER_API_KEY) {
      requestOptions.headers['Authorization'] = `Bearer ${FIDER_API_KEY}`;
    }

    const req = httpModule.request(requestOptions, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          const result = {
            statusCode: res.statusCode,
            headers: res.headers,
            body: data ? JSON.parse(data) : null
          };
          resolve(result);
        } catch (e) {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: data
          });
        }
      });
    });

    req.on('error', (err) => {
      reject(err);
    });

    if (options.body) {
      req.write(JSON.stringify(options.body));
    }

    req.end();
  });
}

// MCP tool handlers
const tools = {
  async listPosts(params) {
    const queryParams = new URLSearchParams();
    if (params.query) queryParams.append('query', params.query);
    if (params.view) queryParams.append('view', params.view);
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.tags) queryParams.append('tags', params.tags);

    const url = `${baseUrl}/api/v1/posts?${queryParams.toString()}`;
    
    try {
      const response = await makeRequest(url);
      return {
        content: [{
          type: "text",
          text: `Found ${response.body && response.body.length ? response.body.length : 0} posts:\n\n${JSON.stringify(response.body, null, 2)}`
        }]
      };
    } catch (error) {
      throw new Error(`Failed to list posts: ${error.message}`);
    }
  },

  async getPost(params) {
    if (!params.number) {
      throw new Error("Post number is required");
    }

    const url = `${baseUrl}/api/v1/posts/${params.number}`;
    
    try {
      const response = await makeRequest(url);
      if (response.statusCode === 404) {
        throw new Error(`Post #${params.number} not found`);
      }
      return {
        content: [{
          type: "text",
          text: `Post #${params.number}:\n\n${JSON.stringify(response.body, null, 2)}`
        }]
      };
    } catch (error) {
      throw new Error(`Failed to get post: ${error.message}`);
    }
  },

  async createPost(params) {
    if (!params.title) {
      throw new Error("Post title is required");
    }

    const url = `${baseUrl}/api/v1/posts`;
    const body = {
      title: params.title,
      description: params.description || ""
    };
    
    try {
      const response = await makeRequest(url, {
        method: 'POST',
        body: body
      });
      
      if (response.statusCode >= 400) {
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
      }
      
      return {
        content: [{
          type: "text",
          text: `Post created successfully:\n\n${JSON.stringify(response.body, null, 2)}`
        }]
      };
    } catch (error) {
      throw new Error(`Failed to create post: ${error.message}`);
    }
  },

  async editPost(params) {
    if (!params.number) {
      throw new Error("Post number is required");
    }
    if (!params.title) {
      throw new Error("Post title is required");
    }

    const url = `${baseUrl}/api/v1/posts/${params.number}`;
    const body = {
      title: params.title,
      description: params.description || ""
    };
    
    try {
      const response = await makeRequest(url, {
        method: 'PUT',
        body: body
      });
      
      if (response.statusCode >= 400) {
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
      }
      
      return {
        content: [{
          type: "text",
          text: `Post #${params.number} updated successfully`
        }]
      };
    } catch (error) {
      throw new Error(`Failed to edit post: ${error.message}`);
    }
  },

  async deletePost(params) {
    if (!params.number) {
      throw new Error("Post number is required");
    }

    const url = `${baseUrl}/api/v1/posts/${params.number}`;
    const body = {
      text: params.reason || "Deleted via MCP"
    };
    
    try {
      const response = await makeRequest(url, {
        method: 'DELETE',
        body: body
      });
      
      if (response.statusCode >= 400) {
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
      }
      
      return {
        content: [{
          type: "text",
          text: `Post #${params.number} deleted successfully`
        }]
      };
    } catch (error) {
      throw new Error(`Failed to delete post: ${error.message}`);
    }
  },

  async respondToPost(params) {
    if (!params.number) {
      throw new Error("Post number is required");
    }
    if (!params.status) {
      throw new Error("Status is required");
    }

    const validStatuses = ['open', 'planned', 'started', 'completed', 'declined', 'duplicate'];
    if (!validStatuses.includes(params.status)) {
      throw new Error(`Invalid status. Must be one of: ${validStatuses.join(', ')}`);
    }

    if (params.status === 'duplicate' && !params.originalNumber) {
      throw new Error("originalNumber is required when status is 'duplicate'");
    }

    const url = `${baseUrl}/api/v1/posts/${params.number}/status`;
    const body = {
      status: params.status,
      text: params.text || ""
    };

    if (params.originalNumber) {
      body.originalNumber = params.originalNumber;
    }
    
    try {
      const response = await makeRequest(url, {
        method: 'PUT',
        body: body
      });
      
      if (response.statusCode >= 400) {
        throw new Error(`HTTP ${response.statusCode}: ${JSON.stringify(response.body)}`);
      }
      
      return {
        content: [{
          type: "text",
          text: `Post #${params.number} status updated to '${params.status}' successfully`
        }]
      };
    } catch (error) {
      throw new Error(`Failed to respond to post: ${error.message}`);
    }
  }
};

// Track if server is initialized
let initialized = false;

rl.on('line', async (line) => {
  console.error(`Received line: ${line}`);
  try {
    const request = JSON.parse(line);
    console.error(`Parsed request: ${JSON.stringify(request)}`);

    if (request.method === 'initialize') {
      const result = {
        protocolVersion: "2024-11-05",
        capabilities: {
          tools: {}
        },
        serverInfo: {
          name: 'Fider MCP Server',
          version: '1.0.0'
        }
      };
      sendResponse(request.id, result);
    } 
    else if (request.method === 'initialized') {
      console.error("Client initialized - server ready for requests.");
      initialized = true;
      // Don't send a response to initialized notification
    }
    else if (request.method === 'tools/call') {
      const { name, arguments: args } = request.params;
      
      try {
        let result;
        switch (name) {
          case 'list_posts':
            result = await tools.listPosts(args || {});
            break;
          case 'get_post':
            result = await tools.getPost(args || {});
            break;
          case 'create_post':
            result = await tools.createPost(args || {});
            break;
          case 'edit_post':
            result = await tools.editPost(args || {});
            break;
          case 'delete_post':
            result = await tools.deletePost(args || {});
            break;
          case 'respond_to_post':
            result = await tools.respondToPost(args || {});
            break;
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
        
        sendResponse(request.id, result);
      } catch (error) {
        console.error(`Tool execution error: ${error.message}`);
        sendError(request.id, -32603, `Tool execution failed: ${error.message}`);
      }
    }
    else if (request.method === 'tools/list') {
      // Return list of available tools with full schemas
      const toolsList = [
        {
          name: "list_posts",
          description: "List posts from Fider with optional filtering",
          inputSchema: {
            type: "object",
            properties: {
              query: {
                type: "string",
                description: "Search keywords"
              },
              view: {
                type: "string",
                description: "Filter and order. Options: all, recent, my-votes, most-wanted, most-discussed, planned, started, completed, declined, trending",
                enum: ["all", "recent", "my-votes", "most-wanted", "most-discussed", "planned", "started", "completed", "declined", "trending"]
              },
              limit: {
                type: "integer",
                description: "Number of entries to return (default: 30)",
                minimum: 1,
                maximum: 100
              },
              tags: {
                type: "string",
                description: "Comma-separated list of tags to filter by"
              }
            }
          }
        },
        {
          name: "get_post",
          description: "Get a specific post by its number",
          inputSchema: {
            type: "object",
            properties: {
              number: {
                type: "integer",
                description: "The post number to retrieve"
              }
            },
            required: ["number"]
          }
        },
        {
          name: "create_post",
          description: "Create a new post (requires authentication)",
          inputSchema: {
            type: "object",
            properties: {
              title: {
                type: "string",
                description: "The title of the post"
              },
              description: {
                type: "string",
                description: "The description of the post"
              }
            },
            required: ["title"]
          }
        },
        {
          name: "edit_post",
          description: "Edit an existing post (requires collaborator/admin role)",
          inputSchema: {
            type: "object",
            properties: {
              number: {
                type: "integer",
                description: "The post number to edit"
              },
              title: {
                type: "string",
                description: "The new title of the post"
              },
              description: {
                type: "string",
                description: "The new description of the post"
              }
            },
            required: ["number", "title"]
          }
        },
        {
          name: "delete_post",
          description: "Delete a post (requires admin role)",
          inputSchema: {
            type: "object",
            properties: {
              number: {
                type: "integer",
                description: "The post number to delete"
              },
              reason: {
                type: "string",
                description: "Reason for deletion"
              }
            },
            required: ["number"]
          }
        },
        {
          name: "respond_to_post",
          description: "Respond to a post by changing its status (requires collaborator/admin role)",
          inputSchema: {
            type: "object",
            properties: {
              number: {
                type: "integer",
                description: "The post number to respond to"
              },
              status: {
                type: "string",
                description: "The new status of the post",
                enum: ["open", "planned", "started", "completed", "declined", "duplicate"]
              },
              text: {
                type: "string",
                description: "Optional description of the status change"
              },
              originalNumber: {
                type: "integer",
                description: "Required when status is 'duplicate' - the post number to merge into"
              }
            },
            required: ["number", "status"]
          }
        }
      ];
      
      sendResponse(request.id, { tools: toolsList });
    }
    else {
      console.error(`Unhandled method: ${request.method}`);
      if (request.id !== undefined) {
        sendError(request.id, -32601, 'Method not found');
      }
    }
  } catch (e) {
    console.error("Error parsing JSON or processing request:", e);
    if (e.message.includes('JSON')) {
      // JSON parsing error
      sendError(null, -32700, 'Parse error');
    }
  }
});

rl.on('close', () => {
  console.error("Readline interface closed - server shutting down.");
});

// Prevent the process from exiting on uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.error('Received SIGINT, shutting down gracefully...');
  rl.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.error('Received SIGTERM, shutting down gracefully...');
  rl.close();
  process.exit(0);
});

console.error("Fider MCP server is ready to receive messages.");
console.error(`Base URL: ${baseUrl}`);
console.error(`API Key configured: ${FIDER_API_KEY ? 'Yes' : 'No'}`);
#!/usr/bin/env python3
"""
Fider MCP Server - A Model Context Protocol server for Fider API integration.

This server provides tools to interact with a Fider instance via the MCP protocol.
"""

import asyncio
import json
import os
import sys
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode, urlparse
import aiohttp

# Configure logging to stderr to keep stdout clean for JSON-RPC
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('fider-mcp-server')

# Configuration from environment variables
FIDER_BASE_URL = os.environ.get('FIDER_BASE_URL', os.environ.get('FIDER_URL', 'https://your-fider-instance.com')).rstrip('/')
FIDER_API_KEY = os.environ.get('FIDER_API_KEY', '')


class FiderMCPServer:
    """MCP Server for Fider API integration."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the MCP server and listen for JSON-RPC messages on stdin."""
        logger.info("Fider MCP server started")
        logger.info(f"Base URL: {FIDER_BASE_URL}")
        logger.info(f"API Key configured: {'Yes' if FIDER_API_KEY else 'No'}")
        
        # Create aiohttp session
        headers = {'User-Agent': 'Fider-MCP-Server/1.0.0'}
        if FIDER_API_KEY:
            headers['Authorization'] = f'Bearer {FIDER_API_KEY}'
        
        self.session = aiohttp.ClientSession(headers=headers)
        
        try:
            # Read from stdin line by line
            reader = asyncio.StreamReader()
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: asyncio.StreamReaderProtocol(reader), sys.stdin
            )
            
            while True:
                line = await reader.readline()
                if not line:
                    break
                    
                await self.handle_message(line.decode().strip())
                
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            if self.session:
                await self.session.close()
                
    async def handle_message(self, message: str):
        """Handle incoming JSON-RPC message."""
        if not message:
            return
            
        logger.debug(f"Received: {message}")
        
        try:
            request = json.loads(message)
            
            if request.get('method') == 'initialize':
                await self.handle_initialize(request)
            elif request.get('method') == 'initialized':
                logger.info("Client initialized - server ready for requests")
            elif request.get('method') == 'tools/list':
                await self.handle_tools_list(request)
            elif request.get('method') == 'tools/call':
                await self.handle_tool_call(request)
            else:
                if 'id' in request:
                    await self.send_error(request['id'], -32601, 'Method not found')
                    
        except json.JSONDecodeError as e:
            await self.send_error(None, -32700, f'Parse error: {str(e)}')
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if 'id' in locals() and 'request' in locals() and 'id' in request:
                await self.send_error(request['id'], -32603, f'Internal error: {str(e)}')
                
    async def send_response(self, id: Any, result: Any):
        """Send JSON-RPC response."""
        response = {
            'jsonrpc': '2.0',
            'id': id,
            'result': result
        }
        message = json.dumps(response)
        print(message, flush=True)
        logger.debug(f"Sent response: {message}")
        
    async def send_error(self, id: Any, code: int, message: str, data: Any = None):
        """Send JSON-RPC error response."""
        response = {
            'jsonrpc': '2.0',
            'id': id,
            'error': {
                'code': code,
                'message': message
            }
        }
        if data is not None:
            response['error']['data'] = data
            
        error_message = json.dumps(response)
        print(error_message, flush=True)
        logger.debug(f"Sent error: {error_message}")
        
    async def handle_initialize(self, request: Dict[str, Any]):
        """Handle initialize request."""
        result = {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'tools': {}
            },
            'serverInfo': {
                'name': 'Fider MCP Server',
                'version': '1.0.0'
            }
        }
        await self.send_response(request['id'], result)
        
    async def handle_tools_list(self, request: Dict[str, Any]):
        """Handle tools/list request."""
        tools = [
            {
                'name': 'list_posts',
                'description': 'List posts from Fider with optional filtering',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'Search keywords'
                        },
                        'view': {
                            'type': 'string',
                            'description': 'Filter and order. Options: all, recent, my-votes, most-wanted, most-discussed, planned, started, completed, declined, trending',
                            'enum': ['all', 'recent', 'my-votes', 'most-wanted', 'most-discussed', 'planned', 'started', 'completed', 'declined', 'trending']
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Number of entries to return (default: 30)',
                            'minimum': 1,
                            'maximum': 100
                        },
                        'tags': {
                            'type': 'string',
                            'description': 'Comma-separated list of tags to filter by'
                        }
                    }
                }
            },
            {
                'name': 'get_post',
                'description': 'Get a specific post by its number',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'number': {
                            'type': 'integer',
                            'description': 'The post number to retrieve'
                        }
                    },
                    'required': ['number']
                }
            },
            {
                'name': 'create_post',
                'description': 'Create a new post (requires authentication)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'title': {
                            'type': 'string',
                            'description': 'The title of the post'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'The description of the post'
                        }
                    },
                    'required': ['title']
                }
            },
            {
                'name': 'edit_post',
                'description': 'Edit an existing post (requires collaborator/admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'number': {
                            'type': 'integer',
                            'description': 'The post number to edit'
                        },
                        'title': {
                            'type': 'string',
                            'description': 'The new title of the post'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'The new description of the post'
                        }
                    },
                    'required': ['number', 'title']
                }
            },
            {
                'name': 'delete_post',
                'description': 'Delete a post (requires admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'number': {
                            'type': 'integer',
                            'description': 'The post number to delete'
                        },
                        'reason': {
                            'type': 'string',
                            'description': 'Reason for deletion'
                        }
                    },
                    'required': ['number']
                }
            },
            {
                'name': 'respond_to_post',
                'description': 'Respond to a post by changing its status (requires collaborator/admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'number': {
                            'type': 'integer',
                            'description': 'The post number to respond to'
                        },
                        'status': {
                            'type': 'string',
                            'description': 'The new status of the post',
                            'enum': ['open', 'planned', 'started', 'completed', 'declined', 'duplicate']
                        },
                        'text': {
                            'type': 'string',
                            'description': 'Optional description of the status change'
                        },
                        'originalNumber': {
                            'type': 'integer',
                            'description': "Required when status is 'duplicate' - the post number to merge into"
                        }
                    },
                    'required': ['number', 'status']
                }
            },
            {
                'name': 'list_comments',
                'description': 'List comments for a specific post',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'number': {
                            'type': 'integer',
                            'description': 'The post number to get comments for'
                        }
                    },
                    'required': ['number']
                }
            },
            {
                'name': 'add_comment',
                'description': 'Add a comment to a post (requires authentication)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'number': {
                            'type': 'integer',
                            'description': 'The post number to comment on'
                        },
                        'content': {
                            'type': 'string',
                            'description': 'The comment content'
                        }
                    },
                    'required': ['number', 'content']
                }
            },
            {
                'name': 'update_comment',
                'description': 'Update a comment (requires authentication and ownership)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_number': {
                            'type': 'integer',
                            'description': 'The post number'
                        },
                        'comment_id': {
                            'type': 'integer',
                            'description': 'The comment ID to update'
                        },
                        'content': {
                            'type': 'string',
                            'description': 'The new comment content'
                        }
                    },
                    'required': ['post_number', 'comment_id', 'content']
                }
            },
            {
                'name': 'delete_comment',
                'description': 'Delete a comment (requires authentication and ownership/admin)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_number': {
                            'type': 'integer',
                            'description': 'The post number'
                        },
                        'comment_id': {
                            'type': 'integer',
                            'description': 'The comment ID to delete'
                        }
                    },
                    'required': ['post_number', 'comment_id']
                }
            },
            {
                'name': 'list_tags',
                'description': 'List all available tags',
                'inputSchema': {
                    'type': 'object',
                    'properties': {}
                }
            },
            {
                'name': 'create_tag',
                'description': 'Create a new tag (requires admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'The tag name'
                        },
                        'color': {
                            'type': 'string',
                            'description': 'The tag color (hex format, e.g., #FF0000)'
                        },
                        'isPublic': {
                            'type': 'boolean',
                            'description': 'Whether the tag is public (default: true)'
                        }
                    },
                    'required': ['name', 'color']
                }
            },
            {
                'name': 'update_tag',
                'description': 'Update an existing tag (requires admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'slug': {
                            'type': 'string',
                            'description': 'The tag slug to update'
                        },
                        'name': {
                            'type': 'string',
                            'description': 'The new tag name'
                        },
                        'color': {
                            'type': 'string',
                            'description': 'The new tag color (hex format, e.g., #FF0000)'
                        },
                        'isPublic': {
                            'type': 'boolean',
                            'description': 'Whether the tag is public'
                        }
                    },
                    'required': ['slug', 'name', 'color']
                }
            },
            {
                'name': 'delete_tag',
                'description': 'Delete a tag (requires admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'slug': {
                            'type': 'string',
                            'description': 'The tag slug to delete'
                        }
                    },
                    'required': ['slug']
                }
            },
            {
                'name': 'assign_tag',
                'description': 'Assign a tag to a post (requires collaborator/admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_number': {
                            'type': 'integer',
                            'description': 'The post number'
                        },
                        'slug': {
                            'type': 'string',
                            'description': 'The tag slug to assign'
                        }
                    },
                    'required': ['post_number', 'slug']
                }
            },
            {
                'name': 'unassign_tag',
                'description': 'Unassign a tag from a post (requires collaborator/admin role)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_number': {
                            'type': 'integer',
                            'description': 'The post number'
                        },
                        'slug': {
                            'type': 'string',
                            'description': 'The tag slug to unassign'
                        }
                    },
                    'required': ['post_number', 'slug']
                }
            }
        ]
        
        await self.send_response(request['id'], {'tools': tools})
        
    async def handle_tool_call(self, request: Dict[str, Any]):
        """Handle tools/call request."""
        params = request.get('params', {})
        tool_name = params.get('name')
        args = params.get('arguments', {})
        
        try:
            if tool_name == 'list_posts':
                result = await self.list_posts(args)
            elif tool_name == 'get_post':
                result = await self.get_post(args)
            elif tool_name == 'create_post':
                result = await self.create_post(args)
            elif tool_name == 'edit_post':
                result = await self.edit_post(args)
            elif tool_name == 'delete_post':
                result = await self.delete_post(args)
            elif tool_name == 'respond_to_post':
                result = await self.respond_to_post(args)
            elif tool_name == 'list_comments':
                result = await self.list_comments(args)
            elif tool_name == 'add_comment':
                result = await self.add_comment(args)
            elif tool_name == 'update_comment':
                result = await self.update_comment(args)
            elif tool_name == 'delete_comment':
                result = await self.delete_comment(args)
            elif tool_name == 'list_tags':
                result = await self.list_tags(args)
            elif tool_name == 'create_tag':
                result = await self.create_tag(args)
            elif tool_name == 'update_tag':
                result = await self.update_tag(args)
            elif tool_name == 'delete_tag':
                result = await self.delete_tag(args)
            elif tool_name == 'assign_tag':
                result = await self.assign_tag(args)
            elif tool_name == 'unassign_tag':
                result = await self.unassign_tag(args)
            else:
                raise ValueError(f'Unknown tool: {tool_name}')
                
            await self.send_response(request['id'], result)
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            await self.send_error(request['id'], -32603, f'Tool execution failed: {str(e)}')
            
    async def make_request(self, method: str, path: str, json_data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Fider API."""
        url = f"{FIDER_BASE_URL}{path}"
        
        async with self.session.request(method, url, json=json_data, params=params) as response:
            text = await response.text()
            
            try:
                data = json.loads(text) if text else None
            except json.JSONDecodeError:
                data = text
                
            if response.status >= 400:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"HTTP {response.status}: {data}"
                )
                
            return data
            
    async def list_posts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List posts from Fider."""
        params = {}
        if args.get('query'):
            params['query'] = args['query']
        if args.get('view'):
            params['view'] = args['view']
        if args.get('limit'):
            params['limit'] = str(args['limit'])
        if args.get('tags'):
            params['tags'] = args['tags']
            
        data = await self.make_request('GET', '/api/v1/posts', params=params)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Found {len(data) if isinstance(data, list) else 0} posts:\n\n{json.dumps(data, indent=2)}"
            }]
        }
        
    async def get_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific post."""
        if not args.get('number'):
            raise ValueError('Post number is required')
            
        try:
            data = await self.make_request('GET', f"/api/v1/posts/{args['number']}")
            return {
                'content': [{
                    'type': 'text',
                    'text': f"Post #{args['number']}:\n\n{json.dumps(data, indent=2)}"
                }]
            }
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise ValueError(f"Post #{args['number']} not found")
            raise
            
    async def create_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new post."""
        if not args.get('title'):
            raise ValueError('Post title is required')
            
        body = {
            'title': args['title'],
            'description': args.get('description', '')
        }
        
        data = await self.make_request('POST', '/api/v1/posts', json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Post created successfully:\n\n{json.dumps(data, indent=2)}"
            }]
        }
        
    async def edit_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Edit an existing post."""
        if not args.get('number'):
            raise ValueError('Post number is required')
        if not args.get('title'):
            raise ValueError('Post title is required')
            
        body = {
            'title': args['title'],
            'description': args.get('description', '')
        }
        
        await self.make_request('PUT', f"/api/v1/posts/{args['number']}", json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Post #{args['number']} updated successfully"
            }]
        }
        
    async def delete_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a post."""
        if not args.get('number'):
            raise ValueError('Post number is required')
            
        body = {
            'text': args.get('reason', 'Deleted via MCP')
        }
        
        await self.make_request('DELETE', f"/api/v1/posts/{args['number']}", json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Post #{args['number']} deleted successfully"
            }]
        }
        
    async def respond_to_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Respond to a post by changing its status."""
        if not args.get('number'):
            raise ValueError('Post number is required')
        if not args.get('status'):
            raise ValueError('Status is required')
            
        valid_statuses = ['open', 'planned', 'started', 'completed', 'declined', 'duplicate']
        if args['status'] not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            
        if args['status'] == 'duplicate' and not args.get('originalNumber'):
            raise ValueError("originalNumber is required when status is 'duplicate'")
            
        body = {
            'status': args['status'],
            'text': args.get('text', '')
        }
        
        if args.get('originalNumber'):
            body['originalNumber'] = args['originalNumber']
            
        await self.make_request('PUT', f"/api/v1/posts/{args['number']}/status", json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Post #{args['number']} status updated to '{args['status']}' successfully"
            }]
        }
        
    # Comment methods
    async def list_comments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List comments for a specific post."""
        if not args.get('number'):
            raise ValueError('Post number is required')
            
        data = await self.make_request('GET', f"/api/v1/posts/{args['number']}/comments")
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Comments for post #{args['number']}:\n\n{json.dumps(data, indent=2)}"
            }]
        }
        
    async def add_comment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a comment to a post."""
        if not args.get('number'):
            raise ValueError('Post number is required')
        if not args.get('content'):
            raise ValueError('Comment content is required')
            
        body = {
            'content': args['content']
        }
        
        data = await self.make_request('POST', f"/api/v1/posts/{args['number']}/comments", json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Comment added successfully to post #{args['number']}:\n\n{json.dumps(data, indent=2)}"
            }]
        }
        
    async def update_comment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update a comment."""
        if not args.get('post_number'):
            raise ValueError('Post number is required')
        if not args.get('comment_id'):
            raise ValueError('Comment ID is required')
        if not args.get('content'):
            raise ValueError('Comment content is required')
            
        body = {
            'content': args['content']
        }
        
        await self.make_request('PUT', f"/api/v1/posts/{args['post_number']}/comments/{args['comment_id']}", json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Comment #{args['comment_id']} updated successfully"
            }]
        }
        
    async def delete_comment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a comment."""
        if not args.get('post_number'):
            raise ValueError('Post number is required')
        if not args.get('comment_id'):
            raise ValueError('Comment ID is required')
            
        await self.make_request('DELETE', f"/api/v1/posts/{args['post_number']}/comments/{args['comment_id']}")
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Comment #{args['comment_id']} deleted successfully"
            }]
        }
        
    # Tag methods
    async def list_tags(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all available tags."""
        data = await self.make_request('GET', '/api/v1/tags')
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Available tags:\n\n{json.dumps(data, indent=2)}"
            }]
        }
        
    async def create_tag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tag."""
        if not args.get('name'):
            raise ValueError('Tag name is required')
        if not args.get('color'):
            raise ValueError('Tag color is required')
            
        body = {
            'name': args['name'],
            'color': args['color'],
            'isPublic': args.get('isPublic', True)
        }
        
        data = await self.make_request('POST', '/api/v1/tags', json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Tag created successfully:\n\n{json.dumps(data, indent=2)}"
            }]
        }
        
    async def update_tag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing tag."""
        if not args.get('slug'):
            raise ValueError('Tag slug is required')
        if not args.get('name'):
            raise ValueError('Tag name is required')
        if not args.get('color'):
            raise ValueError('Tag color is required')
            
        body = {
            'name': args['name'],
            'color': args['color'],
            'isPublic': args.get('isPublic', True)
        }
        
        data = await self.make_request('PUT', f"/api/v1/tags/{args['slug']}", json_data=body)
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Tag '{args['slug']}' updated successfully:\n\n{json.dumps(data, indent=2)}"
            }]
        }
        
    async def delete_tag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a tag."""
        if not args.get('slug'):
            raise ValueError('Tag slug is required')
            
        await self.make_request('DELETE', f"/api/v1/tags/{args['slug']}")
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Tag '{args['slug']}' deleted successfully"
            }]
        }
        
    async def assign_tag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a tag to a post."""
        if not args.get('post_number'):
            raise ValueError('Post number is required')
        if not args.get('slug'):
            raise ValueError('Tag slug is required')
            
        await self.make_request('POST', f"/api/v1/posts/{args['post_number']}/tags/{args['slug']}")
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Tag '{args['slug']}' assigned to post #{args['post_number']} successfully"
            }]
        }
        
    async def unassign_tag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Unassign a tag from a post."""
        if not args.get('post_number'):
            raise ValueError('Post number is required')
        if not args.get('slug'):
            raise ValueError('Tag slug is required')
            
        await self.make_request('DELETE', f"/api/v1/posts/{args['post_number']}/tags/{args['slug']}")
        
        return {
            'content': [{
                'type': 'text',
                'text': f"Tag '{args['slug']}' unassigned from post #{args['post_number']} successfully"
            }]
        }


def main():
    """Main entry point for script execution."""
    async def run_server():
        server = FiderMCPServer()
        try:
            await server.start()
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)
    
    asyncio.run(run_server())


if __name__ == '__main__':
    main()
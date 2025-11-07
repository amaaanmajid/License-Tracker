from typing import Dict, List
from sqlalchemy.orm import Session
import os
from openai import OpenAI
import json

class AIAssistantService:
    """
    AI Assistant Service using OpenAI GPT-3.5-Turbo with Direct MCP Integration
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Import MCP handlers directly - no HTTP needed!
        from services.mcp_handlers import MCPHandlers
        self.mcp_handlers = MCPHandlers(db)
    
    def get_available_tools(self) -> List[Dict]:
        """Get available tools from MCP handlers"""
        # Define tools directly instead of fetching via HTTP
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_licenses",
                    "description": "Get all licenses or filter by status (valid, expired, expiring)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status_filter": {
                                "type": "string",
                                "enum": ["valid", "expired", "expiring_30_days", "all"],
                                "description": "Filter by license status"
                            },
                            "limit": {"type": "integer", "default": 20}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_devices",
                    "description": "Get all devices or filter by status and location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["ACTIVE", "MAINTENANCE", "DECOMMISSIONED", "all"]},
                            "location": {"type": "string"},
                            "limit": {"type": "integer", "default": 20}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_license_utilization",
                    "description": "Get license utilization statistics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "threshold_percentage": {"type": "number", "default": 0}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_expiring_licenses",
                    "description": "Get licenses expiring within specified days",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "default": 30}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_devices_at_risk",
                    "description": "Get devices with expired or expiring licenses",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days_threshold": {"type": "integer", "default": 15}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_vendor_analysis",
                    "description": "Get vendor analysis and license distribution",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_licenses",
                    "description": "Search licenses by software name or license key",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_devices",
                    "description": "Search devices by ID, type, or location",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_dashboard_summary",
                    "description": "Get comprehensive dashboard summary",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_assignments_for_device",
                    "description": "Get all license assignments for a specific device",
                    "parameters": {
                        "type": "object",
                        "properties": {"device_id": {"type": "string"}},
                        "required": ["device_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_assignments_for_license",
                    "description": "Get all device assignments for a specific license",
                    "parameters": {
                        "type": "object",
                        "properties": {"license_key": {"type": "string"}},
                        "required": ["license_key"]
                    }
                }
            }
        ]
        
        return tools
    
    def call_mcp_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool directly via MCP handlers (no HTTP)"""
        try:
            # Route to appropriate handler
            if tool_name == "get_licenses":
                result = self.mcp_handlers.get_licenses(arguments)
            elif tool_name == "get_devices":
                result = self.mcp_handlers.get_devices(arguments)
            elif tool_name == "get_license_utilization":
                result = self.mcp_handlers.get_license_utilization(arguments)
            elif tool_name == "get_expiring_licenses":
                result = self.mcp_handlers.get_expiring_licenses(arguments)
            elif tool_name == "get_devices_at_risk":
                result = self.mcp_handlers.get_devices_at_risk(arguments)
            elif tool_name == "get_vendor_analysis":
                result = self.mcp_handlers.get_vendor_analysis(arguments)
            elif tool_name == "search_licenses":
                result = self.mcp_handlers.search_licenses(arguments)
            elif tool_name == "search_devices":
                result = self.mcp_handlers.search_devices(arguments)
            elif tool_name == "get_dashboard_summary":
                result = self.mcp_handlers.get_dashboard_summary(arguments)
            elif tool_name == "get_assignments_for_device":
                result = self.mcp_handlers.get_assignments_for_device(arguments)
            elif tool_name == "get_assignments_for_license":
                result = self.mcp_handlers.get_assignments_for_license(arguments)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
            
            return json.dumps(result, indent=2, default=str)
        
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def process_query(self, user_query: str, conversation_history: List[Dict] = None) -> Dict:
        """Process user query using GPT-3.5-Turbo with Direct MCP"""
        
        if conversation_history is None:
            conversation_history = []
        
        # Get tools
        tools = self.get_available_tools()
        
        if not tools:
            return {
                "success": False,
                "query": user_query,
                "response": "I'm having trouble accessing the database tools. Please try again.",
                "error": "MCP unavailable"
            }
        
        # Build messages
        messages = [
            {
                "role": "system",
                "content": """You are a helpful AI assistant for a License Tracker system managing network devices and software licenses for telecom companies.

You have access to database tools via MCP (Model Context Protocol). Use them to provide accurate, data-driven responses.

**Response Guidelines:**
- Always use tools to get real data before answering
- Be concise and clear
- Use bullet points for lists
- Highlight critical issues: 🔴 expired, ⚠️ warning, ✅ ok
- Suggest actionable next steps when relevant"""
            }
        ] + conversation_history + [
            {"role": "user", "content": user_query}
        ]
        
        try:
            # First API call to OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # Check if the model wants to call tools
            if tool_calls:
                # Add assistant's response to messages
                messages.append(response_message)
                
                # Execute each tool call directly
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Call MCP handler directly
                    function_response = self.call_mcp_tool(function_name, function_args)
                    
                    # Add tool response to messages
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
                
                # Get final response from OpenAI
                second_response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1500
                )
                
                final_message = second_response.choices[0].message.content
                tools_used = [tc.function.name for tc in tool_calls]
                
                return {
                    "success": True,
                    "query": user_query,
                    "response": final_message,
                    "tools_used": tools_used,
                    "tokens_used": response.usage.total_tokens + second_response.usage.total_tokens
                }
            
            else:
                # No tool call needed
                return {
                    "success": True,
                    "query": user_query,
                    "response": response_message.content,
                    "tools_used": [],
                    "tokens_used": response.usage.total_tokens
                }
        
        except Exception as e:
            return {
                "success": False,
                "query": user_query,
                "response": f"I encountered an error: {str(e)}",
                "error": str(e)
            }
    
    def get_suggested_queries(self) -> List[str]:
        """Return suggested queries"""
        return [
            "Which licenses are expiring soon?",
            "Show me the dashboard summary",
            "What devices don't have licenses?",
            "How are my licenses being utilized?",
            "Which vendors have the most licenses?",
            "Are there any expired licenses?",
            "Show me devices at risk",
            "Search for Windows licenses",
            "Give me a summary of my inventory"
        ]
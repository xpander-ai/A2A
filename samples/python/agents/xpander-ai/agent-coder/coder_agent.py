import asyncio
import inspect
from typing import Optional
import boto3
from os import environ
from dotenv import load_dotenv
from xpander_sdk import Agent, LLMProvider, XpanderClient, ToolCallResult, ToolCallType
from local_tools import local_tools_by_name, local_tools_list
# Load environment variables
load_dotenv()

# AWS config
AWS_PROFILE = environ.get("AWS_PROFILE")
AWS_REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

class CoderAgent:
    """Agent handling Bedrock interaction"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.agent.select_llm_provider(LLMProvider.AMAZON_BEDROCK)
        self.agent.add_local_tools(local_tools_list)
        # Setup Bedrock client
        if AWS_PROFILE:
            session = boto3.Session(profile_name=AWS_PROFILE)
            self.bedrock = session.client("bedrock-runtime", region_name=AWS_REGION)
        else:
            self.bedrock = boto3.client(
                "bedrock-runtime", 
                region_name=AWS_REGION, 
                aws_access_key_id=environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=environ.get("AWS_SECRET_ACCESS_KEY")
            )
        
        # Configure tools
        self.tool_config = {
            "tools": agent.get_tools(), 
            "toolChoice": {"any": {} if agent.tool_choice == 'required' else False}
        }
    def chat(self,user_input: str, thread_id: Optional[str] = None):
        """
        Starts the conversation with the user and handles the interaction with Bedrock.
        """
        if thread_id:
            print(f"🧠 Adding task to existing thread : {thread_id}")
            self.agent.add_task(input=user_input, thread_id=thread_id)
        else:
            print("🧠 Adding task to a new thread")
            self.agent.add_task(input=user_input)
        agent_thread = self._agent_loop()
        print(f"\n🧠 Thread {agent_thread.memory_thread_id}\n🤖 Agent response: {agent_thread.result}")
        return agent_thread.memory_thread_id

    def _agent_loop(self):
        """Run the agent interaction loop"""
        step = 1
        print("🪄 Starting Agent Loop")
        while not self.agent.is_finished():
            print("-"*80)
            print(f"🔍 Step {step}")
            
            # Get model response
            response = self.bedrock.converse(
                modelId=MODEL_ID,
                messages=self.agent.messages,
                toolConfig=self.tool_config,
                system=self.agent.memory.system_message
            )
            self.agent.add_messages(response)

            ## Parallel execution of tools
            
            # Execute tools if needed
            tool_calls = self.agent.extract_tool_calls(llm_response=response)
            
            # execute non local tools - in parallel
            cloud_tool_call_results = self.agent.run_tools(tool_calls=tool_calls)
            
            # retrieve tool calls for local execution
            local_tool_calls = XpanderClient.retrieve_pending_local_tool_calls(tool_calls=tool_calls)
            cloud_tool_call_results[:] = [c for c in cloud_tool_call_results if c.tool_call_id not in {t.tool_call_id for t in local_tool_calls}]
            
            # execute local tools - in parallel
            local_tool_call_results = asyncio.run(self._execute_local_tools_in_parallel(local_tool_calls))

            # report local tool call results
            if len(local_tool_call_results) != 0:
                self.agent.memory.add_tool_call_results(tool_call_results=local_tool_call_results)
            
            # print the results
            all_tool_call_results = cloud_tool_call_results + local_tool_call_results
            
            for result in all_tool_call_results:
                emoji = "✅" if result.is_success else "❌"
                print(f"{emoji} {result.function_name}")
                
            step += 1
            
        return self.agent.retrieve_execution_result()

    async def _execute_local_tools_in_parallel(self, local_tool_calls):
        tasks = [self._execute_local_tool(tool) for tool in local_tool_calls]
        return await asyncio.gather(*tasks)
    
    async def _execute_local_tool(self, tool):
        print(f"🔦 Executing local tool: {tool.name} with generated payload: {tool.payload}")
        tool_call_result = ToolCallResult(function_name=tool.name, tool_call_id=tool.tool_call_id, payload=tool.payload)
        
        # Validate parameters for both async and non-async functions
        sig = inspect.signature(local_tools_by_name[tool.name])
        valid_params = sig.parameters.keys()
        invalid_params = [k for k in tool.payload.keys() if k not in valid_params]
        if invalid_params:
            return {
                "success": False, 
                "message": f"Invalid parameters for {tool.name}: {', '.join(invalid_params)}",
                "invalid_params": invalid_params
            }
        
        # Execute the function based on its type
        if asyncio.iscoroutinefunction(local_tools_by_name[tool.name]):
            local_tool_response = await local_tools_by_name[tool.name](**tool.payload)
        else:
            # Create a wrapper function that handles the unpacking of kwargs
            def run_func():
                return local_tools_by_name[tool.name](**tool.payload)
                
            loop = asyncio.get_event_loop()
            local_tool_response = await loop.run_in_executor(None, run_func)

        if 'success' in local_tool_response:
            if local_tool_response['success']:
                tool_call_result.is_success = True
            else:
                tool_call_result.is_success = False

        tool_call_result.result = local_tool_response
        return tool_call_result
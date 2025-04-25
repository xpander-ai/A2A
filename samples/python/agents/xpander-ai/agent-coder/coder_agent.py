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
            
            # Execute tools if needed
            tool_calls = self.agent.extract_tool_calls(
                llm_response=response
            )
            
            for tool in tool_calls:
                if tool.type == ToolCallType.LOCAL:
                    print(f"🛠️ Executing local tool: {tool.name}")
                    ## Prepare tool call object
                    tool_call_result = ToolCallResult(function_name=tool.name,tool_call_id=tool.tool_call_id,payload=tool.payload)
                    payload_from_function = local_tools_by_name[tool.name](**tool.payload)
                    if('success' in payload_from_function):
                        if(payload_from_function['success']):
                            tool_call_result.is_success = True
                        else:
                            tool_call_result.is_error = True
                    tool_call_result.result = payload_from_function
                    self.agent.memory.add_tool_call_results(tool_call_results=[tool_call_result])
                    print(f"✅ {tool_call_result.function_name}" if tool_call_result.is_success else f"❌ {tool_call_result.function_name}")
                if tool.type == ToolCallType.XPANDER:
                    print(f"🛠️ Executing cloud tool: {tool.name}")
                    result : ToolCallResult = self.agent.run_tool(tool=tool)
                    print(f"✅ {result.function_name}" if result.is_success else f"❌ {result.function_name}")
            ## Tool_calls will now contain remaining local tool calls if any
            
            # # Run local tools (If any)
            # pending_local_tool_execution = XpanderClient.retrieve_pending_local_tool_calls(tool_calls=tool_calls)
            # if pending_local_tool_execution:
            #     local_tools_results = []
            #     for tc in pending_local_tool_execution:
            #         print(f"Extracting payload for local tool: {tc.name}")
            #         tool_call_result = ToolCallResult(function_name=tc.name, tool_call_id=tc.tool_call_id, payload=tc.payload)
            #         try:
            #             if tc.name in local_tools_by_name:
            #                 tool_call_result.is_success = True
            #                 print(f"🛠️ Executing local tool: {tc.name}")
            #                 tool_call_result.result = local_tools_by_name[tc.name](**tc.payload)
            #             else:
            #                 raise Exception(f"Local tool {tc.name} not found")
            #         except Exception as e:
            #             tool_call_result.is_success = False
            #             tool_call_result.is_error = True
            #             tool_call_result.result = str(e)
            #         finally:
            #             local_tools_results.append(tool_call_result)

            #     if local_tools_results:
            #         print(f"📝 Registering {len(local_tools_results)} local tool results...")
            #         self.agent.memory.add_tool_call_results(tool_call_results=local_tools_results)
           
            step += 1
            
        return self.agent.retrieve_execution_result()

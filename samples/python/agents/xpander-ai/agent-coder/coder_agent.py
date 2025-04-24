from typing import Optional
import boto3
from os import environ
from dotenv import load_dotenv
from xpander_sdk import Agent, LLMProvider, XpanderClient

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
            if tool_calls:
                print("🧩 Tools: " + " | ".join(f"{call.name}" for call in tool_calls))
                results = self.agent.run_tools(tool_calls=tool_calls)
                print(" | ".join(
                    f"✅ {r.function_name}" if r.is_success else f"❌ {r.function_name}"
                    for r in results
                ))
            step += 1
            
        return self.agent.retrieve_execution_result()

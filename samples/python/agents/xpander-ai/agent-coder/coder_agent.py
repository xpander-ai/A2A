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

    def __init__(self, agent: Agent, xpander_client: XpanderClient):
        self.agent = agent
        self.xpander_client = xpander_client
        
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
            "tools": agent.get_tools(LLMProvider.AMAZON_BEDROCK), 
            "toolChoice": {"any": {} if agent.tool_choice == 'required' else False}
        }

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
            tool_calls = self.xpander_client.extract_tool_calls(
                llm_response=response, 
                llm_provider=LLMProvider.AMAZON_BEDROCK
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
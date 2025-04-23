import json
from typing import Optional
import boto3
from xpander_sdk import XpanderClient, Agent, LLMProvider, Execution
from xpander_utils.events import AgentExecution
from os import environ
from dotenv import load_dotenv
load_dotenv()

# Optional values with fallback
AWS_PROFILE = environ.get("AWS_PROFILE")  # returns None if not set
AWS_ACCESS_KEY_ID = environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
XPANDER_API_KEY=environ.get("XPANDER_API_KEY")
xpander_client = XpanderClient(api_key=XPANDER_API_KEY)

class CoderAgent:
    """
    Coder Agent class
    """

    def __init__(self, agent: Optional[Agent] = None):
        if AWS_PROFILE:
            print(f"Using profile: {AWS_PROFILE}")
            session = boto3.Session(profile_name=AWS_PROFILE)
            self.bedrockRuntimeClient = session.client(
                "bedrock-runtime", region_name=AWS_REGION
            )
        else:
            self.bedrockRuntimeClient = boto3.client(
                "bedrock-runtime", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
        if agent:
            self.agent = agent
        else:
            self.agent = xpander_client.agents.create(name="Coder Agent")
        try:
            with open('xpander_config.json', 'r') as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            config = {}
            
        config.update({
            'organization_id': self.agent.organization_id,
            'api_key': XPANDER_API_KEY,
            'agent_id': self.agent.id
        })
        
        with open('xpander_config.json', 'w') as config_file:
            json.dump(config, config_file, indent=2)
        self.tool_config = {"tools" : self.agent.get_tools(LLMProvider.AMAZON_BEDROCK), "toolChoice": { "any": {} if self.agent.tool_choice == 'required' else False }}

    def runtask(self, execution_task: AgentExecution) -> Execution:
        """
        Starts the conversation with the user and handles the interaction with Bedrock.
        """
        self.agent.init_task(execution=execution_task.model_dump())
        self.agent.memory.llm_provider = LLMProvider.AMAZON_BEDROCK
        execution_status = self._agent_loop(self.agent)
        return execution_status
    
    def invoke_agent(self, user_input: str, thread_id: Optional[str] = None):
        """
        Starts the conversation with the user and handles the interaction with Bedrock.
        """
        if thread_id:
            print(f"🧠 Adding task to existing thread : {thread_id}")
            self.agent.add_task(input=user_input, thread_id=thread_id)
        else:
            print("🧠 Adding task to a new thread")
            self.agent.add_task(input=user_input)

        self.agent.memory.llm_provider = LLMProvider.AMAZON_BEDROCK
        agent_thread = self._agent_loop(self.agent)

        print(f"\n🧠 Thread {agent_thread.memory_thread_id}\n🤖 Agent response: {agent_thread.result}")
        return agent_thread.memory_thread_id
    
    def _agent_loop(self, agent: Agent):
        step = 1
        print("🪄 Starting Agent Loop")
        while not agent.is_finished():
            print("-"*100)
            print(f"🔍 Agent Step : {step}")
            response = self.bedrockRuntimeClient.converse(
                modelId=MODEL_ID,
                messages=agent.messages,
                toolConfig=self.tool_config,
                system=agent.memory.system_message
            )
            print("💬 Adding LLM response to thread")
            agent.add_messages(response)            
            tool_calls = XpanderClient.extract_tool_calls(llm_response=response, llm_provider=LLMProvider.AMAZON_BEDROCK)
            if tool_calls:
                print("🔍 Executing functions selected by the AI:")
                print(" | ".join(f"🧩 Tool: {call.name}" for call in tool_calls))

                tools_results = agent.run_tools(tool_calls=tool_calls)
                print(" | ".join(
                    f"✅ {res.function_name}" if res.is_success else f"❌ {res.function_name}"
                    for res in tools_results
                ))
                print("Done running tools")
            step += 1
        return agent.retrieve_execution_result()
    
def main():
    with open('xpander_config.json', 'r') as config_file:
        config = json.load(config_file)
        if not config.get('agent_id'):
            coder_agent = CoderAgent()
        else:
            coder_agent = CoderAgent(agent=xpander_client.agents.get(config['agent_id']))

    # coder_agent.runtask(execution_task=AgentExecution(input="Hello, how are you?"))
    thread = coder_agent.invoke_agent(user_input="Hello, how are you?")
    print(f"🧠 Thread ID: {thread}")
if __name__ == "__main__":
    main()
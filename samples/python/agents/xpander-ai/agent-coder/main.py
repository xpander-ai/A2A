from xpander import get_agent
from coder_agent import CoderAgent

if __name__ == "__main__":
    agent = get_agent() ## will come from the CLI
    coder_agent = CoderAgent(agent=agent)
    # result = run_task(AgentExecution(input="Hello, how are you?"))
    thread = coder_agent.chat("Hello, what's your role?")    
    while True:
        user_input = input("You: ")
        coder_agent.chat(user_input, thread)
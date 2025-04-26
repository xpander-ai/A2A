"""
Copyright (c) 2025 Xpander, Inc. All rights reserved.
"""

from xpander import get_agent
from coder_agent import CoderAgent

if __name__ == "__main__":
    agent = get_agent() ## will come from the CLI
    coder_agent = CoderAgent(agent=agent)
    # result = run_task(AgentExecution(input="Hello, how are you?"))
    thread = coder_agent.chat("Your task is to update the xpander-ai/docs with a new tutorial on how to use https://github.com/xpander-ai/A2A/tree/add-coder-agent-tutorial the coder agent with xpander")    
    while True:
        user_input = input("You: ")
        coder_agent.chat(user_input, thread)
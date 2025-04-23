# Coder Agent (Python/Bedrock)

This is a Python version of the code-writing agent that emits full code files as artifacts. It uses Amazon Bedrock instead of Gemini. Start it with:

```bash
export XPANDER_API_KEY=<your_xpander_api_key>
export XPANDER_AGENT_ID=<your_xpander_agent_id>
# Configure AWS credentials via any of these methods:
export AWS_PROFILE=<your_aws_profile>  # OR
export AWS_ACCESS_KEY_ID=<your_aws_access_key>
export AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>

python -m samples.python.agents.coder.coder_agent
```

This will start up the agent on `http://localhost:41241/`.

## Requirements

Before running, make sure to install the required dependencies:

```bash
pip install xpander-sdk boto3 python-dotenv a2a-sdk
``` 
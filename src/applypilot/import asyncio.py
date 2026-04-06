import asyncio

from browser_use.llm.deepseek.chat import ChatDeepSeek
from browser_use import Agent

async def main():
    # Initialize DeepSeek as an OpenAI-compatible model
    llm = ChatDeepSeek(
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key="sk-cf465a18f9e1419693e9311b0ab0749b"
    )
    
    # Define the task
    agent = Agent(
        task="Go to Reddit, search for 'browser-use', and return the first comment.",
        llm=llm,
        use_vision=False  # Required for DeepSeek compatibility
    )

    result = await agent.run()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())

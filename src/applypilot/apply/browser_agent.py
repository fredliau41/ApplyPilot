import os
import asyncio
import logging
from applypilot import config
from applypilot.apply import prompt as prompt_mod

# Suppress browser_use noisy stdout logs that break the dashboard and Live UI
import browser_use
logging.getLogger("browser_use").setLevel(logging.CRITICAL)
# Remove their default handler which writes to stderr
for handler in logging.getLogger("browser_use").handlers[:]:
    logging.getLogger("browser_use").removeHandler(handler)

from browser_use import Agent, Browser
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.llm.anthropic.chat import ChatAnthropic

logger = logging.getLogger(__name__)

async def run_job_browser_use(job: dict, worker_id: int, model: str = "claude-3-5-sonnet-latest", dry_run: bool = False, headless: bool = False) -> tuple[str, int]:
    """Spanws a browser-use Agent to handle the job application."""
    import time
    start = time.time()
    
    from dotenv import load_dotenv
    load_dotenv(config.ENV_PATH)
    
    # Check for custom LLM configuration
    openai_key = os.environ.get("OPENAI_API_KEY")
    local_url = os.environ.get("LLM_URL")
    llm_api_key = os.environ.get("LLM_API_KEY", openai_key)
    model_override = os.environ.get("LLM_MODEL", model)

    if local_url or openai_key:
        if "deepseek" in model_override.lower():
            from browser_use.llm.deepseek.chat import ChatDeepSeek
            llm = ChatDeepSeek(
                model=model_override,
                base_url=local_url,
                api_key=llm_api_key
            )
        else:
            llm = ChatOpenAI(
                model=model_override,
                base_url=local_url,
                api_key=llm_api_key
            )
    else:
        # Default to Anthropic if no OpenAI/OpenRouter config is found
        if model == "sonnet":
            model = "claude-3-5-sonnet-latest"
        elif model == "haiku":
            model = "claude-3-haiku-20240307"
        llm = ChatAnthropic(model=model)
    
    # Get prompt text and file paths
    # We will modify prompt.py so it returns (instruction_string, resume_pdf_path, cover_letter_pdf_path)
    instruction, resume_path, cover_letter_path = prompt_mod.build_prompt_browser_use(job, dry_run=dry_run)
    
    available_files = []
    if resume_path:
        available_files.append(resume_path)
    if cover_letter_path:
        available_files.append(cover_letter_path)
        
    browser = Browser(
        headless=headless,
        executable_path=config.get_chrome_path(),
        user_data_dir=config.get_chrome_user_data(),
        args=["--disable-blink-features=AutomationControlled"], # Helps avoid detection
    )
    
    agent = Agent(
        task=instruction,
        llm=llm,
        browser=browser,
        available_file_paths=available_files
    )
    
    history = await agent.run()
    
    if history.has_errors():
        return "failed:agent_error", int((time.time() - start) * 1000)
    
    # We can check history.is_successful() if available in this version.
    
    last_msg = history.final_result() if hasattr(history, 'final_result') else str(history)
    
    await browser.close()
    
    # Simple check for applied status
    result = "applied" if "RESULT:APPLIED" in last_msg else f"failed:{last_msg[:20]}"
    return result, int((time.time() - start) * 1000)

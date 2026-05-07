import warnings
warnings.filterwarnings("ignore")

import autogen
from dotenv import load_dotenv
import os
import sys
import logging
from io import StringIO
import concurrent.futures
from tools import search_papers
from prompts import SYSTEM_PROMPT

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()

LLM_CONFIG = {
    "config_list": [
        {
            "model": "open-mistral-nemo",
            "api_key": os.getenv("MISTRAL_API_KEY"),
            "api_type": "mistral",
            "api_rate_limit": 0.25,
            "repeat_penalty": 1.1,
            "temperature": 0.0,
            "seed": 42,
            "stream": False,
            "native_tool_calls": False,
            "cache_seed": None,
        }
    ]
}

assistant = autogen.AssistantAgent(
    name="ResearchScout",
    system_message=SYSTEM_PROMPT,
    llm_config=LLM_CONFIG,
)

user_proxy = autogen.UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,
    code_execution_config=False,
    is_termination_msg=lambda msg: (content := msg.get("content")) and (
        "Why this paper:" in content or
        "No paper was found" in content
    ),
)


autogen.register_function(
    search_papers,
    caller=assistant,
    executor=user_proxy,
    name="search_papers",
    description="Search for academic papers by topic. Use year_after/year_before for range constraints, or year_exact for a specific year. Returns title, authors, year, citation count, DOI, and abstract.",
)

_run_logger = logging.getLogger("run")

def run(prompt, timeout=30):
    _run_logger.info("--- prompt: %s", prompt)
    original_stdout = sys.stdout
    sys.stdout = StringIO()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(user_proxy.initiate_chat, assistant, message=prompt, silent=True)
        try:
            result = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            sys.stdout = original_stdout
            print("\nNo paper was found that satisfies all constraints.")
            return

    sys.stdout = original_stdout
    final = next(
        (m["content"] for m in reversed(result.chat_history)
         if m.get("content") and (
             "Why this paper:" in m["content"] or
             "No paper was found" in m["content"]
         )),
        None,
    )
    if final:
        print("\n" + final)
    else:
        print("\nNo answer was returned.")


def _ask_str(label: str, default: str) -> str:
    raw = input(f"  {label} [default: {default}]: ").strip()
    return raw if raw else default


def _ask_int(label: str, default: int) -> int:
    raw = input(f"  {label} [default: {default}]: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"  Invalid input, using default ({default}).")
        return default


def _ask_choice(label: str, default: str, options: list) -> str:
    opts = "/".join(options)
    while True:
        raw = input(f"  {label} ({opts}) [default: {default}]: ").strip().lower()
        if not raw:
            return default
        if raw in [o.lower() for o in options]:
            return raw
        print(f"  Please enter one of: {opts}")


def _ask(label: str, default, options=None):
    if options is not None:
        return _ask_choice(label, default, options)
    if isinstance(default, int):
        return _ask_int(label, default)
    return _ask_str(label, default)


PRESET_PROMPTS = [
    {
        "label": "Detailed search (prompt: Find a research paper about [topic] published [before/after/in] [year] and has at least [amount] citations)",
        "params": [
            ("Topic", "LLM agents for software engineering"),
            ("Before/after/in", "after"),
            ("Published after year", 2022),
            ("Minimum citations", 100),
        ],
        "build": lambda p: (
            f"Find a research paper about {p[0]} that was published "
            f"{p[1]} {p[2]} and has at least {p[3]} citations. Explain why the paper is relevant "
            f"and provide the source of the citation count."
        ),
    },
    {
        "label": "Quick search (prompt: Find a recent paper about [topic] and explain whether it would be useful for [activity/profession])",
        "params": [
            ("Topic", "AI agents using tools"),
            ("Activity/profession", "someone building autonomous agents"),
        ],
        "build": lambda p: (
            f"Find a recent paper about {p[0]} and explain whether it would be "
            f"useful for {p[1]}."
        ),
    },
]


def main():
    print("\n=== Research Scout Agent ===\n")
    print("Choose a prompt template:\n")
    for i, preset in enumerate(PRESET_PROMPTS, 1):
        print(f"  {i}. {preset['label']}")
    print()

    while True:
        raw = input("Enter choice (1-2): ").strip()
        if raw in ("1", "2"):
            choice = int(raw) - 1
            break
        print("  Please enter 1 or 2")

    preset = PRESET_PROMPTS[choice]
    values = []

    if preset["params"]:
        print()
        for label, default in preset["params"]:
            values.append(_ask(label, default))

    prompt = preset["build"](values)
    print("\nSearching...", flush=True)
    run(prompt)


if __name__ == "__main__":
    main()
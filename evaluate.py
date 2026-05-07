import io
import sys
import json
from agent import run

# Prompt 1 — detailed search: topic, before/after/in, year, min citations
PROMPT1_TESTS = [
    ("Geology",                          "before", 2020,   200),   # broad, after
    ("Keynesian Economics",               "before", 2026,    50),   # narrow, before
    ("Computer vision object detection", "after",  2022,   500),   # narrow, high citations
    ("Political Science",                "in",     2018,   100),   # broad, exact year
    ("Geothermics of Iceland",           "after",  2000,    30),   # very narrow/niche
    ("AI alignment",                     "after",  2025, 10000),   # impossible
]

# Prompt 2 — quick search: topic, activity/profession
PROMPT2_TESTS = [
    ("Geology",                       "a civil engineer designing infrastructure"), # narrow, very specific
    ("Economics",                                                   "a physicist"), # broad, very generic (unusual combination)
    ("Computer science",                                  "a university lecturer"), # broad, mildly generic
    ("Anarcho-Capitalism and decentralized governance",    "a political theorist"), # narrow, specific
    ("Computer vision object detection",                    "a robotics engineer"), # narrow, specific
    ("Linguistics",               "a data scientist working with social networks"), # broad, very specific (unusual combination)
]

def build_prompt1(topic, direction, year, citations):
    return (
        f"Find a research paper about {topic} that was published "
        f"{direction} {year} and has at least {citations} citations. "
        f"Explain why the paper is relevant and provide the source of the citation count."
    )

def build_prompt2(topic, activity):
    return (
        f"Find a recent paper about {topic} and explain whether it would be useful for {activity}."
    )

def capture_run(prompt):
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        run(prompt)
    except Exception as e:
        sys.stdout = sys.__stdout__
        return f"ERROR: {e}"
    sys.stdout = sys.__stdout__
    return buffer.getvalue().strip()

def evaluate():
    results = []
    total = len(PROMPT1_TESTS) + len(PROMPT2_TESTS)
    test_id = 1

    groups = [
        ("Prompt 1 — detailed search", [
            (build_prompt1(*args), args) for args in PROMPT1_TESTS
        ]),
        ("Prompt 2 — quick search", [
            (build_prompt2(*args), args) for args in PROMPT2_TESTS
        ]),
    ]

    for group_label, tests in groups:
        print(f"\n=== {group_label} ===")
        for prompt, params in tests:
            print(f"\n--- Test {test_id}/{total} ---")
            print(f"Params: {params}")
            output = capture_run(prompt)
            results.append({
                "test_id": test_id,
                "group": group_label,
                "params": list(params),
                "prompt": prompt,
                "output": output,
            })
            print("Done.")
            test_id += 1

    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nAll {total} tests done. Results saved to evaluation_results.json")

if __name__ == "__main__":
    evaluate()

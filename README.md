# Research Scout Agent

An AI research assistant that searches for academic papers based on user constraints such as topic, publication year, and citation count. Built with AutoGen and the OpenAlex API, using Mistral's open-mistral-nemo as the reasoning model.

## Setup

### 1. Install Python 3.12
This project requires Python 3.12.

### 2. Create a virtual environment

> **bash/zsh shell**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```
For other users of other shells replace second line with:

> **Fish shell:** `source .venv/bin/activate.fish`
> **PowerShell:** `.venv\Scripts\Activate.ps1`


### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

Create a .env file in the project root:
MISTRAL_API_KEY=your_key_here
Get a free API key at https://console.mistral.ai

## Running the agent

Make sure you are in the directory of this solution and in the virtual environment.

```bash
python agent.py
```

## Running the evaluation

```bash
python evaluate.py
```

Results will be saved in evaluation_results.json.

## How it works

1. The user submits their choice of the 2 predefined prompts whereafter the user specifies the parameters such as topic, minimum citations.
A detailed search which takes more parameters and a quick search that helps finding a paper fitting a specific user but without any other parameters such as publishing year and citations.
2. The CLI collects constraints from the user (topic, year, min. citations) and formats them into a prompt string, which is passed to the AutoGen AssistantAgent.
The agent is implemented as an AutoGen two-agent loop: an AssistantAgent (ResearchScout) decides when and how to call the tool, while a UserProxyAgent executes the tool call and checks whether the response satisfies the termination condition.
3. The agent calls the `search_papers` tool with the constraints.
4. The tool queries the OpenAlex API and filters results deterministically.
5. The agent selects the most relevant paper and returns a structured answer.

## Evaluation results

12 tests were run, 6 for each of the 2 prompt options. Tests cover broad and narrow topics, before/after/exact year constraints, high citation thresholds, a niche topic likely to return no results, and an impossible constraint.

For each test the conclusion notes whether the agent found a relevant paper, respected the constraints, and gave a useful explanation. This approach is based on RAG evaluation principles (faithfulness, answer relevance, source grounding), adapted for a tool-using agent where year and citation constraints can be verified directly against the returned data.

### Prompt 1 — detailed search

| # | Topic | When | Min cit. | Type | Result | Conclusion |
|---|-------|------|----------|------|--------|------------|
| 1 | Geology | before 2020 | 200 | Broad | ⚠️ Partial | Returned *The Continental Crust* (1985, 11123 cit.). Directly about geology, all constraints met. No link was provided however. |
| 2 | Keynesian Economics | before 2026 | 50 | Narrow | ⚠️ Partial | Returned *The Affluent Society* (1958, 1981 cit.). Constraints met but the book addresses post-scarcity economics broadly, not Keynesian theory specifically. |
| 3 | Computer vision object detection | after 2022 | 500 | Narrow, high citations | ✅ Pass | Returned YOLOv7 (2023, 10657 cit.). Directly on-topic, all constraints met. |
| 4 | Political Science | in 2018 | 100 | Broad, exact year | ⚠️ Partial | Returned a 2018 paper on misinformation spread (8172 cit.). Year and citation constraints met but the topic is adjacent to political science rather than a direct match. |
| 5 | Geothermics of Iceland | after 2000 | 30 | Very niche | ⚠️ Partial | Returned a supercritical geothermal systems paper (2017, 221 cit.) that references Iceland but is not specifically about Iceland. |
| 6 | AI alignment | after 2025 | 10000 | Impossible | ✅ Pass | Correctly rejected with no hallucinated paper. |

### Prompt 2 — quick search

| # | Topic | For whom | Type | Result | Conclusion |
|---|-------|----------|------|--------|------------|
| 7 | Geology | A civil engineer designing infrastructure | Broad, specific audience | ✅ Pass | Returned SoilGrids 2.0 (2021, 1961 cit.), a global soil mapping paper directly useful for infrastructure siting and design. |
| 8 | Economics | A physicist | Broad, mismatched audience | ⚠️ Partial | Returned an input-output analysis textbook (2021, 5118 cit.). On-topic for economics but the explanation of usefulness to a physicist draws a tenuous parallel rather than a genuine one. |
| 9 | Computer science | A university lecturer | Broad | ✅ Pass | Returned a CNN survey paper (2021, 4686 cit.). Directly about computer science with a clear explanation of relevance to a lecturer. |
| 10 | Anarcho-Capitalism and decentralized governance | A political theorist | Narrow, niche | ⚠️ Partial | Returned a paper on blockchain-based commons governance (2021, 34 cit.). Relevant to decentralised governance but does not address anarcho-capitalism directly. |
| 11 | Computer vision object detection | A robotics engineer | Narrow, specific | ✅ Pass | Returned Swin Transformer (2021, 29228 cit.). Directly relevant with a clear explanation of practical use for a robotics engineer. |
| 12 | Linguistics | A data scientist working with social networks | Broad, mismatched audience | ✅ Pass | Returned mT5 (2021, 1530 cit.), a multilingual NLP model. Relevant to linguistics and genuinely applicable to analysing multilingual social network text data. |

## Reflection

**What worked well:** Enforcing year and citation constraints through the OpenAlex API rather than relying on the LLM to judge them was the most important design decision. All constraint failures in early testing were due to the LLM picking papers that did not actually meet the criteria. Once filtering moved to deterministic code in the tool, this stopped happening entirely. The `year_exact` parameter and the timeout mechanism (tests 3 and 8 previously hung indefinitely) also worked reliably. After adding retry logic and stricter keyword filtering, the pass rate improved from 1/6 to 3/6 on Prompt 1 and from 1/6 to 4/6 on Prompt 2.

**What failed or was unreliable:** Topic relevance was a persistent weak point. The model (open-mistral-nemo) frequently accepted papers that were adjacent to the requested topic rather than squarely about it. For example, returning a general geothermal systems paper for "Geothermics of Iceland", or *The Affluent Society* for "Keynesian Economics".It was also inconsistent in detection of audiance relevance: test 8 (Economics for a physicist) produced an explanation that argued the connection rather than evaluating it honestly. Niche topics were harder than broad ones because OpenAlex returned less material, leaving the model with a small pool to choose from.

**How often did the agent need tool calls:** 11 out of 12 tests used exactly one tool call. Only test 8 (Economics, physicist) triggered a retry but the log shows the agent reused the identical query (`Economics`, year_after=2020) rather than refining it, so both calls returned the same 3 results. No test exceeded two calls. The log also shows the agent occasionally rephrased queries on the first call without being asked: test 5 sent `geothermics Iceland` instead of the literal topic string, and test 10 used `anarcho-capitalism AND decentralized governance` with an explicit AND operator.

**Did the LLM ever hallucinate:** Yes, in early testing. When no paper met the constraints, the model invented plausible-sounding titles, authors, and citation counts rather than admitting failure. In one case it also cited "Google Scholar" as the source rather than OpenAlex, which is a hallucination of the citation source since all data comes from the tool. This was partially mitigated by the system prompt rule forbidding invented data, but the source label issue persists because the model is not always consistent about which attribution to use.

**How did you prevent incorrect answers:** Three mechanisms work together. First, all paper data (title, year, citations, DOI, abstract) is returned by the tool and the LLM is instructed never to use values it did not receive from the tool results. Second, the tool applies year and citation filters at the API level, so no out-of-range paper reaches the model. Third, the system prompt instructs the agent to reject a paper if it has to argue why it is related, and to output a fixed "No paper was found" string when nothing qualifies which the termination condition and output parser both detect cleanly.

**What would I improve with more time:** Firstly, the most impactful change would be switching to a stronger model with better instruction-following and relevance judgment. Secondly, returning a relevance score alongside each paper from the tool (based on how many query terms match and where) would give the model a clearer signal for ranking candidates.

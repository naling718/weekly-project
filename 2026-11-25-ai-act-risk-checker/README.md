# AI Act Risk Checker

A small tool that reads a plain-English description of an AI system and sorts it into one of the EU AI Act's four risk tiers: unacceptable, high, limited or minimal. It shows which article or Annex III area matched, the words that triggered it, and what obligations follow. You can use it from the command line, in a web page, or through a JSON API.

It is a first-pass triage tool, not legal advice.

## The problem behind it

- Disseqt AI, an AI governance startup based at NovaUCD, raised about $8M in November 2026 to test and monitor enterprise AI systems for safety and compliance ([YourStory](https://yourstory.com/2026/11/disseqt-ai-raises-8m-to-build-enterprise-ai-safeguards), [IT Brief](https://itbrief.co.uk/story/disseqt-ai-raises-usd-8-million-to-expand-governance)).
- The Law Society of Ireland says many Irish firms are still unclear on their AI Act obligations, and lists 2 December 2026 as a new compliance date ([Law Society](https://www.lawsociety.ie/news/news/Stories/the-eu-ai-act-in-2026/)).
- The Digital Omnibus on AI, Regulation (EU) 2026/1744, moved the Annex III high-risk duties to 2 December 2027 and the Annex I product duties to 2 August 2028 ([Lewis Silkin](https://www.lewissilkin.com/insights/2026/07/27/the-digital-omnibus-on-ai-enters-into-force-today-102nedo), [Leaseurope](https://www.leaseurope.org/new-application-dates-high-risk-ai-system-rules)).

The first thing any compliance team has to do is work out which tier each of its AI systems falls into. This tool automates that first step and shows its reasoning, so a person can check it.

## Run it

```bash
pip install -r requirements.txt
python check.py --samples          # or: python check.py "your description"
python app.py                      # then open http://localhost:5000
```

Tests: `python -m pytest -q`. Result: 23 passed.

## Example output

```
$ python check.py "Webcam software that reads the emotions of employees during calls"

Result
  Tier: UNACCEPTABLE
  - Art. 5(1)(f) Emotion recognition at work or in education (matched: "emotions of employee")
  Obligations:
    * Banned in the EU since 2 February 2025 (Art. 5). It cannot be placed on the market or used.
    * Fines up to EUR 35m or 7% of worldwide annual turnover (Art. 99(3)).
```

```
$ curl -X POST localhost:5000/api/classify -H 'Content-Type: application/json' \
    -d '{"description":"Ranks job applications and filters CVs"}'
{"tier": "high", "matches": [{"ref": "Annex III(4)", "title": "Employment and worker management", "evidence": "job applica", ...}], "obligations": [...]}
```

The web page has one text box and a "Check risk tier" button. Below it you get a coloured tier badge, a "Why" list of matched articles with the words that matched, and a "What applies" list of obligations.

## How it works

- `classifier.py` holds 20 rules. Each rule has a tier, a legal reference (Art. 5, Annex III, Art. 6(1), Art. 50), regex patterns, and optional exceptions. For example, the credit-scoring rule skips descriptions that mention fraud, because the Act carves out fraud detection.
- The highest matching tier wins. Every match is still listed, so a chatbot that screens job candidates shows both Annex III(4) and Art. 50(1).
- No match means minimal risk.
- `samples.json` has 14 labelled examples. The test suite and `check.py --samples` both use them.

## Design choices and trade-offs

- **Rules, not a trained model.** I had no labelled dataset, and for a legal check you need to be able to say why a system got its tier. Every result points to an article and the exact words that matched. The cost is recall: a description that uses different words will be missed.
- **Highest tier wins.** This matches how the Act works: a high-risk chatbot still has the Art. 50 transparency duties, but the high-risk duties are the ones that matter most.
- **One Flask file with an inline template.** The app is a single page, so a templates folder would add nothing. Jinja escapes user input (there is a test for this).
- **Input limits.** Descriptions are capped at 5,000 characters, and empty or non-string input returns a 400 error.

## What was left out

- The TF-IDF / ML classifier from the original plan. It needs a few hundred labelled descriptions to be better than the rules.
- Negation handling. "Does not use facial recognition" still matches.
- The Art. 6(3) exception, where an Annex III system is not high-risk if it only does a narrow, preparatory task.
- General-purpose AI model duties (Arts. 51 to 55), and the roles of provider and deployer.
- Document upload and languages other than English.

## Next steps

1. Collect 200+ labelled descriptions (for example from the EU AI database once it is populated) and compare a TF-IDF + logistic regression model against the rules.
2. Add a follow-up questions step ("Is this a safety component?", "Who is the deployer?") to handle Art. 6(3) and negation.
3. Export a short PDF or Markdown report for a compliance file.

## Interview talking points

1. **Turning a regulation into code.** I mapped Article 5, Annex III and Article 50 to testable rules, and each output cites the article it came from. That forced me to read the Act closely, including exceptions like fraud detection being excluded from the credit-scoring category.
2. **Explainability over accuracy.** I chose rules over ML because a compliance user has to defend the answer. I can explain what that costs (missed paraphrases, no negation) and how I would measure a model against the rules once labelled data exists.
3. **Testing against an independent source.** The expected tiers in the tests come from the Act's own categories, not from running the code. I also test edge cases like "sentence" or "migration" not triggering the justice or border-control rules, and that user input is escaped in the page.

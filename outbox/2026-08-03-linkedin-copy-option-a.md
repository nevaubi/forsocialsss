1,822 court decisions now deal with hallucinated AI content.

913 of them landed in the first seven months of 2026. The rest of the curve: 16 in 2023, 58 in 2024, 821 in 2025.

I pulled the CSV from Damien Charlotin's AI Hallucination Cases database and counted it myself. Three things stood out.

The money is real, and it is not only hitting individuals.

310 decisions record a monetary penalty. In the dollar-denominated slice, 160 sanctions total about $1.2 million.

The largest is $110,204 against two lawyers, with the claims dismissed with prejudice. One order put $31,100 on two law firms jointly.

The lasting cost is not the fine. 126 decisions carry a professional sanction such as a bar referral.

Those opinions are public, indexed and permanent. A fine gets paid once. The search result does not expire.

The part I have not seen discussed: in about 89% of the dated decisions, no tool is named.

The court inferred AI use from the output itself, or the record just says unidentified.

So nobody can measure which system fails most often, and a named vendor usually disputes the attribution.

That is a logging problem, not a legal one.

Four controls carry most of the weight:

- Bind citations to retrieval. If retrieval did not return it, the system does not render it.
- Check existence at egress, on the document that leaves, not in the chat.
- Match quoted language against the source text. 493 decisions involve false quotes, not invented cases.
- Store model, version, prompt and retrieved document IDs with the output.

None of this needs a better model. It needs a verification step with the power to block, and a log that survives the question.

Full report attached. 5 pages, 5 charts, method and limits, every number sourced.

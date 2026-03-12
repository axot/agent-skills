# Output Format Reference

## Template

Every response MUST follow this structure.

For a single question, omit the number: use `*Question: ...*` instead of `*Q1: ...*`.

```
*Q1: <question summary>*
*Answer:*
• answer text <url|_1_> <url|_2_>
> Source: original quoted text
• answer text <url|_1_>
> Source: original quoted text

*Q2: <question summary>*
*Answer:*
• answer text <url|_1_>
> Source: original quoted text
```

## Slack mrkdwn Syntax

Use ONLY Slack mrkdwn. Standard Markdown will render incorrectly in Slack.

| Element | Slack mrkdwn | NOT this |
|---------|-------------|----------|
| Bold | `*bold*` | `**bold**` |
| Italic | `_italic_` | `*italic*` |
| Code | `` `code` `` | same |
| Code block | ` ```code``` ` | same |
| Link | `<https://url\|link text>` | `[text](url)` |
| Quote | `>` at line start | same |
| List | `•` bullet | `-` or `*` |

## Spacing Rules

1. Do NOT emphasize text with bold or italic markers inside answer body; use `*bold*` only for section headers like `*Q1:*` and `*Answer:*`

## Citation Format

Every factual claim requires both a URL citation and an original text quote:

```
• answer text <https://docs.aws.amazon.com/path|_1_>
> Source: <exact text from the source>
```

Multiple sources per point:

```
• answer text <https://url1|_1_> <https://url2|_2_>
> Source: <text from source 1>
> Source: <text from source 2>
```

## EC2 Pricing Output

The bundled scripts output raw text like `Price: 1.0336000000 /hr`. Reformat to match this template:

```
• <instance_type> on-demand pricing in <region>: $X.XXXX/hr, vCPU: N, Memory: N GiB <https://aws.amazon.com/ec2/pricing/on-demand/|_1_>
```

# Output Format Reference

## Template

Every response MUST follow this structure. Answer body text uses 常体/である調.

For a single question, omit the number: use `*質問: ...*` instead of `*質問1: ...*`.

```
*質問1: <question summary>*
*回答:*
• answer text <url|_1_> <url|_2_>
> 原文: original quoted text
• answer text <url|_1_>
> 原文: original quoted text

*質問2: <question summary>*
*回答:*
• answer text <url|_1_>
> 原文: original quoted text
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

1. After Japanese punctuation 、。〜？！（）: always add one space before continuing
2. Around formatting markers `` ` `` and ` ``` ` adjacent to Japanese characters: add spaces on both sides
3. Do NOT emphasize text with bold or italic markers inside answer body; use `*bold*` only for section headers like `*質問1:*` and `*回答:*`

## Citation Format

Every factual claim requires both a URL citation and an original text quote:

```
• <answer in Japanese> <https://docs.aws.amazon.com/path|_1_>
> 原文: <exact text from the source>
```

Multiple sources per point:

```
• <answer in Japanese> <https://url1|_1_> <https://url2|_2_>
> 原文: <text from source 1>
> 原文: <text from source 2>
```

## EC2 Pricing Output

The bundled scripts output raw text like `Price: 1.0336000000 /hr`. Reformat to match this template, adding the dollar sign and converting units to Japanese:

```
• <instance_type> の <region> におけるオンデマンド料金は $X.XXXX/時間、 vCPU: N、 メモリ: N GiB である。 <https://aws.amazon.com/ec2/pricing/on-demand/|_1_>
```

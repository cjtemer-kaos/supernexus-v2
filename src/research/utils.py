import re

THINK_PATTERNS = [
    (r'<think>.*?</think>', re.DOTALL),
    (r'<reason>.*?</reason>', re.DOTALL),
    (r'<thinking>.*?</thinking>', re.DOTALL),
    (r'<thought>.*?</thought>', re.DOTALL),
    (r'<REASONING>.*?</REASONING>', re.DOTALL),
    (r'<REASON>.*?</REASON>', re.DOTALL),
    (r'<THOUGHT>.*?</THOUGHT>', re.DOTALL),
    (r'\[think\].*?\[/think\]', re.DOTALL),
    (r'[Tt]hink(?:ing|):\s*\n(?:.*\n)*?(?=\n\s*\*|\n\s*[A-Z]|\n\s*#|\n\n)', 0),
]

PROMPT_ECHO_PATTERNS = [
    (r'^Here\'?s?(?: is)? (?:the |my |a )?(?:updated |final |full |complete )?(?:report|response|answer|analysis|summary|guide|result)[^:]*:?\s*\n+', re.IGNORECASE),
    (r'^As (?:an?|the) (?:AI|assistant|language model|LLM)[^:]*:?\s*\n+', re.IGNORECASE),
    (r'^I (?:am|will|have|would|can)[^:]*:?\s*\n+', re.IGNORECASE),
    (r'^Let me[^:]*:?\s*\n+', re.IGNORECASE),
    (r'^Sure[^:]*:?\s*\n+', re.IGNORECASE),
    (r'^Of course[^:]*:?\s*\n+', re.IGNORECASE),
    (r'^Certainly[^:]*:?\s*\n+', re.IGNORECASE),
    (r'^Below[^:]*:?\s*\n+', re.IGNORECASE),
]

def strip_think(text: str, prose: bool = False, prompt_echo: bool = True) -> str:
    if not text:
        return text
    for pattern, flags in THINK_PATTERNS:
        text = re.sub(pattern, '', text, flags=flags)
    if prompt_echo:
        for pattern, flags in PROMPT_ECHO_PATTERNS:
            text = re.sub(pattern, '', text, flags=flags)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def strip_thinking(text):
    if text is None:
        return None
    return strip_think(text, prose=False, prompt_echo=True)

LOW_QUALITY_MARKERS = [
    "insufficient to", "content is insufficient", "no substantive data",
    "does not contain", "not relevant to", "no relevant information",
    "unable to extract", "completely unrelated", "boilerplate", "footer text",
    "cookie consent", "cookie banner", "cookie notice", "copyright notice",
    "copyright footer", "all rights reserved",
]

def is_low_quality(summary: str) -> bool:
    try:
        if not summary:
            return True
        low = summary.lower()
        return any(marker in low for marker in LOW_QUALITY_MARKERS)
    except Exception:
        return False

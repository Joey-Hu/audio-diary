import os
from typing import Optional

from langdetect import detect

# Optional OpenAI summarization
_USE_OPENAI = False
try:
    import openai
    _USE_OPENAI = True
except Exception:
    _USE_OPENAI = False

# Local summarizers
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.text_rank import TextRankSummarizer as SumyTextRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

from textrank4zh import TextRank4Sentence


def _openai_summary(text: str, lang: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    # OpenAI python client v1
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    prompt = (
        "请将下面的内容进行结构化总结，给出要点、行动项和结论：\n" if lang == "zh-cn" else
        "Summarize the following transcript with bullet points, action items, and conclusions:\n"
    ) + text
    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "system", "content": "You are a helpful summarization assistant."},
                      {"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def _sumy_summary_en(text: str, sentences_count: int = 5) -> str:
    language = "english"
    parser = PlaintextParser.from_string(text, Tokenizer(language))
    stemmer = Stemmer(language)
    summarizer = SumyTextRankSummarizer(stemmer)
    summarizer.stop_words = get_stop_words(language)
    sentences = summarizer(parser.document, sentences_count)
    return "\n".join(str(s) for s in sentences)


def _textrank_zh(text: str, sentences_count: int = 5) -> str:
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=text, lower=True)
    sents = tr4s.get_key_sentences(num=sentences_count)
    # tr4s returns dicts with 'sentence'
    return "\n".join(s['sentence'] for s in sents)


def summarize_text(text: str) -> str:
    if not text:
        return ""
    try:
        lang_code = detect(text)
    except Exception:
        lang_code = "en"
    is_zh = lang_code.startswith("zh")

    # Try OpenAI first if available
    if _USE_OPENAI and os.getenv("OPENAI_API_KEY"):
        ai_sum = _openai_summary(text, "zh-cn" if is_zh else "en")
        if ai_sum:
            return ai_sum

    # Fall back to local summarizers
    if is_zh:
        return _textrank_zh(text)
    else:
        return _sumy_summary_en(text)

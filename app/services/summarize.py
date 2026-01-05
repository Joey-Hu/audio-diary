import os
from typing import Optional

from langdetect import detect

# Local summarizers
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.text_rank import TextRankSummarizer as SumyTextRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

from textrank4zh import TextRank4Sentence


def _deepseek_summary(text: str, lang: str) -> Optional[str]:
    """使用 DeepSeek API 进行总结，需设置 DEEPSEEK_API_KEY。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        return None
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    client = OpenAI(api_key=api_key, base_url=base_url)
    temperature = float(os.getenv("SUMMARIZE_TEMPERATURE", "0.2"))
    prompt = (
        "请将下面的内容进行结构化总结，给出要点、行动项和结论：\n" if lang == "zh-cn" else
        "Summarize the following transcript with bullet points, action items, and conclusions:\n"
    ) + text
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful summarization assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def _openai_summary(text: str, lang: str) -> Optional[str]:
    """使用 OpenAI 进行总结，需设置 OPENAI_API_KEY。"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        return None
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("SUMMARIZE_TEMPERATURE", "0.2"))
    prompt = (
        "请将下面的内容进行结构化总结，给出要点、行动项和结论：\n" if lang == "zh-cn" else
        "Summarize the following transcript with bullet points, action items, and conclusions:\n"
    ) + text
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful summarization assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
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
    return "\n".join(s['sentence'] for s in sents)


def summarize_text(text: str) -> str:
    if not text:
        return ""
    try:
        lang_code = detect(text)
    except Exception:
        lang_code = "en"
    is_zh = lang_code.startswith("zh")
    lang_tag = "zh-cn" if is_zh else "en"

    # 优先 DeepSeek
    ds_sum = _deepseek_summary(text, lang_tag)
    if ds_sum:
        return ds_sum

    # 其次 OpenAI
    oa_sum = _openai_summary(text, lang_tag)
    if oa_sum:
        return oa_sum

    # 本地兜底
    if is_zh:
        return _textrank_zh(text)
    else:
        return _sumy_summary_en(text)

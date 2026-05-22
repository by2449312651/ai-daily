#!/usr/bin/env python3
"""AI热点日报 — 多源聚合推送钉钉"""

import os
import json
import re
import html
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")


def fetch_json(url: str, timeout: int = 15) -> Optional[dict | list]:
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"[WARN] Fetch failed: {url} — {e}")
        return None


def fetch_bytes(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()
    except Exception as e:
        print(f"[WARN] Fetch failed: {url} — {e}")
        return None


def fetch_text(url: str, timeout: int = 15) -> Optional[str]:
    data = fetch_bytes(url, timeout)
    if data is None:
        return None
    for enc in ("utf-8", "gbk", "gb2312", "utf-16"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def clean_html(raw: str) -> str:
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    return raw.strip()


def fetch_hackernews_ai(top_n: int = 5) -> list[dict]:
    """Hacker News 热门帖（按 AI / 航天关键词过滤）"""
    result = []
    ids = fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not ids:
        return result
    AI_KEYWORDS = {"ai", "artificial intelligence", "machine learning", "deep learning",
                   "llm", "gpt", "chatgpt", "claude", "openai", "gemini", "copilot",
                   "neural", "transformer", "rag", "agent", "diffusion", "multimodal",
                   "vision", "language model", "fine-tun", "embedding", "token",
                   "space", "rocket", "nasa", "spacex", "launch", "satellite",
                   "orbit", "lunar", "mars", "starship", "telescope", "james webb",
                   "astronaut", "太空", "火箭", "卫星", "航天"}
    count = 0
    for sid in ids[:80]:
        item = fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        if not item or not item.get("title"):
            continue
        title = item["title"]
        title_lower = title.lower()
        if any(kw in title_lower for kw in AI_KEYWORDS):
            url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
            score = item.get("score", 0)
            result.append({"title": title, "url": url, "score": score, "source": "Hacker News"})
            count += 1
            if count >= top_n:
                break
    return result


def fetch_github_trending(top_n: int = 5) -> list[dict]:
    """GitHub Trending AI 仓库"""
    result = []
    html_content = fetch_text("https://github.com/trending?since=daily&spoken_language_code=")
    if not html_content:
        return result
    pattern = r'href="/([^"]+)"[^>]*>[^<]*<[^<]*<[^<]*<[^<]*<[^<]*<[^<]*<[^<]*<[^<]*<[^<]*<img'
    repos = re.findall(pattern, html_content)
    if not repos:
        pattern = r'<h2 class="h3 lh-condensed">.*?<a href="/([^"/]+/[^"/]+)"'
        repos = re.findall(pattern, html_content, re.DOTALL)
    desc_pattern = r'<p class="col-9 color-fg-muted my-1 pr-4">(.*?)</p>'
    descs = re.findall(desc_pattern, html_content, re.DOTALL)
    seen = set()
    for i, repo in enumerate(repos):
        if repo in seen:
            continue
        seen.add(repo)
        desc = clean_html(descs[len(seen)-1]) if len(seen)-1 < len(descs) else ""
        result.append({
            "title": repo,
            "url": f"https://github.com/{repo}",
            "desc": desc[:200],
            "source": "GitHub Trending"
        })
        if len(result) >= top_n:
            break
    return result


def fetch_36kr_ai(top_n: int = 5) -> list[dict]:
    """36氪 AI 频道快讯"""
    result = []
    data = fetch_bytes("https://36kr.com/feed", timeout=10)
    if not data:
        return result
    try:
        xml_text = data.decode("utf-8", errors="replace")
        root = ET.fromstring(xml_text)
        ns = {"rss": "http://backend.userapi.com/rss"}
        items = root.findall(".//rss:item", ns) or root.findall(".//item")
        for item in items:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            if not title:
                continue
            keywords = ["ai", "人工智能", "大模型", "GPT", "AI", "模型", "智能", "机器学习", "深度学习", "算法"]
            if any(k in title for k in keywords):
                result.append({"title": title.strip()[:80], "url": link, "source": "36氪"})
                if len(result) >= top_n:
                    break
    except ET.ParseError as e:
        print(f"[WARN] 36kr RSS parse error: {e}")
    return result


def fetch_spacenews(top_n: int = 5) -> list[dict]:
    """SpaceNews 航天新闻"""
    result = []
    data = fetch_bytes("https://spacenews.com/feed", timeout=10)
    if not data:
        return result
    try:
        xml_text = data.decode("utf-8", errors="replace")
        root = ET.fromstring(xml_text)
        items = root.findall(".//item") or []
        for item in items[:top_n]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            if title:
                result.append({"title": title.strip()[:80], "url": link, "source": "航天"})
    except ET.ParseError as e:
        print(f"[WARN] SpaceNews RSS parse error: {e}")
    return result


def fetch_arxiv_space(top_n: int = 5) -> list[dict]:
    """Arxiv 航天/天文最新论文"""
    result = []
    url = "https://export.arxiv.org/api/query?search_query=cat:astro-ph+OR+cat:physics.space-ph&sortBy=submittedDate&sortOrder=descending&max_results=10"
    xml_text = fetch_text(url, timeout=20)
    if not xml_text:
        return result
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        for entry in entries[:top_n]:
            title = clean_html(entry.findtext("atom:title", "", ns))
            link_el = entry.find("atom:id", ns)
            link = link_el.text.strip() if link_el is not None else ""
            summary = clean_html(entry.findtext("atom:summary", "", ns))[:120]
            if any(kw in title.lower() for kw in ("space", "rocket", "satellite", "mars", "lunar", "orbit", "telescope", "galaxy", "exoplanet", "black hole", "solar", "asteroid", "launch")):
                result.append({"title": title[:100], "url": link, "desc": summary, "source": "Arxiv 航天"})
    except ET.ParseError as e:
        print(f"[WARN] Arxiv space parse error: {e}")
    return result


def fetch_arxiv_ai(top_n: int = 5) -> list[dict]:
    """Arxiv AI 最新论文"""
    result = []
    url = "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=10"
    xml_text = fetch_text(url, timeout=20)
    if not xml_text:
        return result
    try:
        root = ET.fromstring(xml_text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom"
        }
        entries = root.findall("atom:entry", ns)
        for entry in entries[:top_n]:
            title = clean_html(entry.findtext("atom:title", "", ns))
            link_el = entry.find("atom:id", ns)
            link = link_el.text.strip() if link_el is not None else ""
            summary = clean_html(entry.findtext("atom:summary", "", ns))[:120]
            result.append({"title": title[:100], "url": link, "desc": summary, "source": "Arxiv AI"})
    except ET.ParseError as e:
        print(f"[WARN] Arxiv parse error: {e}")
    return result


def build_dingtalk_markdown(all_news: list[dict]) -> dict:
    """构建钉钉 Markdown 消息"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 🤖 AI 热点日报 {today}\n"]
    sources_order = [
        ("Hacker News", "🔥"),
        ("GitHub Trending", "⭐"),
        ("Arxiv AI", "📄"),
        ("Arxiv 航天", "🚀"),
        ("航天", "🛰️"),
        ("36氪", "📰"),
    ]
    for src_name, icon in sources_order:
        items = [n for n in all_news if n["source"] == src_name]
        if not items:
            continue
        lines.append(f"## {icon} {src_name}\n")
        for item in items:
            title = item["title"][:80]
            url = item["url"]
            desc = item.get("desc", item.get("score", ""))
            extra = f" — {desc}" if desc else ""
            lines.append(f"- [{title}]({url}){extra}")
        lines.append("")
    lines.append(f"---\n> AI Daily · {datetime.now().strftime('%H:%M')} 自动推送")
    text = "\n".join(lines)
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": f"AI热点日报 {today}",
            "text": text
        }
    }


def push_to_dingtalk(payload: dict):
    if not DINGTALK_WEBHOOK:
        print("[ERROR] DINGTALK_WEBHOOK 未设置，跳过推送")
        return
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DINGTALK_WEBHOOK,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("errcode") == 0:
                print("[OK] 钉钉推送成功")
            else:
                print(f"[WARN] 钉钉推送异常: {body}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"[ERROR] 推送失败: {e}")


def main():
    print("=" * 40)
    print(f"AI Daily 抓取开始 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 40)
    all_news = []
    fetchers = [
        ("Hacker News", fetch_hackernews_ai),
        ("GitHub Trending", fetch_github_trending),
        ("Arxiv AI", fetch_arxiv_ai),
        ("Arxiv 航天", fetch_arxiv_space),
        ("航天", fetch_spacenews),
        ("36氪", fetch_36kr_ai),
    ]
    for name, fn in fetchers:
        try:
            items = fn()
            print(f"  [{name}] {len(items)} 条")
            all_news.extend(items)
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")
    if not all_news:
        print("[WARN] 未抓到任何内容")
        return
    payload = build_dingtalk_markdown(all_news)
    push_to_dingtalk(payload)
    print(f"\n共推送 {len(all_news)} 条热点")


if __name__ == "__main__":
    main()

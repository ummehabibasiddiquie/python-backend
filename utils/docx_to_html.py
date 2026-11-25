# Word .docx → sanitized HTML for the agent Tracker sidebar.

from __future__ import annotations

import base64
import re

import bleach
import mammoth

ALLOWED_TAGS = [
    "p", "br", "div", "span", "figure",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "strong", "b", "em", "i", "u", "s", "sub", "sup",
    "a", "blockquote", "hr", "pre", "img",
]
ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "img": ["src", "alt", "title", "width", "height"],
    "p": ["class"],
    "div": ["class"],
    "span": ["class"],
    "figure": ["class"],
    "blockquote": ["class"],
    "ol": ["class"],
    "ul": ["class"],
    "li": ["class"],
}

STYLE_MAP = """
p[style-name='Title'] => h1:fresh
p[style-name='Subtitle'] => p.sop-lead:fresh
p[style-name='Heading 1'] => h1:fresh
p[style-name='Heading 2'] => h2:fresh
p[style-name='Heading 3'] => h3:fresh
p[style-name='Heading 4'] => h4:fresh
p[style-name='heading 1'] => h1:fresh
p[style-name='heading 2'] => h2:fresh
p[style-name='heading 3'] => h3:fresh
p[style-name='List Number'] => ol > li:fresh
p[style-name='List Bullet'] => ul > li:fresh
p[style-name='Caption'] => p.sop-caption:fresh
p[style-name='Quote'] => blockquote:fresh
p[style-name='Intense Quote'] => blockquote.sop-callout:fresh
r[style-name='Strong'] => strong
"""


def _data_uri(data: bytes, content_type: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


_CALLOUT_RE = re.compile(
    r"<p>(?:\s*<strong>)?\s*(Note|Tip|Warning|Important|Check)\s*:?\s*(?:</strong>)?\s*[:\-–]?\s*(.*?)</p>",
    re.IGNORECASE | re.DOTALL,
)


def enhance_sop_html(html: str) -> str:
    """Turn converted Word HTML into a readable step-by-step guide."""
    html = re.sub(
        r"(<img\b[^>]*>)",
        r'<figure class="sop-shot"><span class="sop-shot-label">Screenshot</span>\1</figure>',
        html,
        flags=re.IGNORECASE,
    )

    def _callout(match):
        kind = match.group(1).strip().lower()
        body = (match.group(2) or "").strip()
        label = match.group(1).strip().title()
        return (
            f'<p class="sop-callout sop-{kind}">'
            f"<strong>{label}</strong> {body}</p>"
        )

    html = _CALLOUT_RE.sub(_callout, html)
    html = re.sub(r"<ol\b(?![^>]*class=)", '<ol class="sop-steps"', html, flags=re.IGNORECASE)
    return html


def convert_docx_to_html(file_obj, save_image=None) -> str:
    """Return sanitized HTML. Raises ValueError if the document cannot be converted.

    save_image(data: bytes, content_type: str) -> str is optional and should
    return a URL. Screenshots fall back to inline data URIs if it is missing
    or fails.
    """
    file_obj.seek(0)

    def convert_image(image):
        with image.open() as image_bytes:
            data = image_bytes.read()
        content_type = getattr(image, "content_type", None) or "image/png"
        src = None
        if save_image:
            try:
                src = save_image(data, content_type)
            except Exception:
                src = None
        if not src:
            src = _data_uri(data, content_type)
        return {"src": src}

    kwargs = {"style_map": STYLE_MAP}
    img_element = getattr(getattr(mammoth, "images", None), "img_element", None)
    if callable(img_element):
        kwargs["convert_image"] = img_element(convert_image)

    result = mammoth.convert_to_html(file_obj, **kwargs)
    html = (result.value or "").strip()
    if not html:
        raise ValueError("This Word document has no readable text")
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=["http", "https", "mailto", "data"],
        strip=True,
    )
    return bleach.linkify(enhance_sop_html(cleaned), parse_email=False)

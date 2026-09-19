"""
Renders brief.html.j2 -> inlines CSS via premailer -> returns the final
HTML string ready to hand to the mailer with the heatmap PNG attached
as a CID image. See outline §3.5 / Phase 4 for why CID and not a hosted
image: Gmail proxies/sometimes blocks remote images, CID has no such
problem since the image travels with the email itself.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from premailer import transform

TEMPLATE_DIR = Path(__file__).parent / "templates"


def build_email_html(countries: list[dict], any_fallback: bool, exec_summary: dict, calendar_events: list[dict], heatmap_boxes: list[dict]) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("brief.html.j2")

    now = datetime.now()  # caller is responsible for ensuring this runs in HKT context / logs it
    raw_html = template.render(
        date=now.strftime("%A, %d %B %Y"),
        generated_time=now.strftime("%H:%M"),
        countries=countries,
        any_fallback=any_fallback,
        exec_summary=exec_summary,
        calendar_events=calendar_events,
        heatmap_boxes=heatmap_boxes,
    )

    # premailer inlines the <style> block into every element's style=""
    # attribute, which is what actually makes this render correctly in
    # Gmail/Outlook — email clients strip <style> tags more often than not.
    inlined = transform(raw_html, keep_style_tags=False)
    return inlined

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "site"
DATA_FILE = SITE_DIR / "site-data.json"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-") or "service"


def prepare_context(data: dict) -> dict:
    phone = data.get("business", {}).get("phone", "")
    phone_digits = re.sub(r"[^\d+]", "", phone)
    context = dict(data)
    context["phone_href"] = f"tel:{phone_digits}" if phone_digits else "#"
    context["current_year"] = __import__("datetime").datetime.now().year

    services = []
    for service in data.get("services", []):
        item = dict(service)
        item["slug"] = service.get("slug") or slugify(service.get("title", "service"))
        services.append(item)
    context["services"] = services
    return context


def render_site(data: dict | None = None) -> None:
    if data is None:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    context = prepare_context(data)
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")

    page_jobs = [
        (SITE_DIR / "index.html", "home.html", ""),
        (SITE_DIR / "about.html", "about.html", ""),
        (SITE_DIR / "contact.html", "contact.html", ""),
        (SITE_DIR / "services" / "index.html", "services-index.html", "../"),
    ]

    for path, template_name, base in page_jobs:
        html = env.get_template(template_name).render(**context, base=base)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        print(f"Rendered {path.relative_to(ROOT)}")

    detail_template = env.get_template("service-detail.html")
    for service in context["services"]:
        path = SITE_DIR / "services" / f"{service['slug']}.html"
        html = detail_template.render(**context, base="../", service=service)
        path.write_text(html, encoding="utf-8")
        print(f"Rendered {path.relative_to(ROOT)}")


if __name__ == "__main__":
    render_site()

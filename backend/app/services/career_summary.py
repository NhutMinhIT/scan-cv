"""Gom work history theo công ty và build career summary."""

import re
from typing import Any

from app.services.date_parser import (
    format_date_mm_yyyy,
    format_duration,
    merge_intervals,
    months_between,
    parse_date_to_month,
)
from app.services.work_history_cleaner import clean_company_name

DOMAIN_KW = [
    "fintech", "banking", "e-commerce", "ecommerce", "automotive", "logistics",
    "healthcare", "education", "saas", "erp", "crm", "insurance", "securities",
    "retail", "manufacturing", "ai", "machine learning", "blockchain",
]

TECH_KW = [
    "react", "next.js", "node.js", "typescript", "javascript", "python", "java",
    "vue", "angular", "fastapi", "nestjs", "docker", "aws", "mongodb", "sql",
    "react native", "microservices", "graphql",
]


def _company_key(company: str) -> str:
    name = clean_company_name(company).lower()
    name = re.sub(r"\b(group|corp|corporation|ltd|inc|jsc|co\.?)\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def _pick_earliest_start(entries: list[dict[str, Any]]) -> str:
    best = ""
    best_idx = 10**9
    for e in entries:
        start = str(e.get("startDate") or "")
        idx = parse_date_to_month(start, end=False) or best_idx
        if idx < best_idx:
            best_idx = idx
            best = start
    return best


def _pick_latest_end(entries: list[dict[str, Any]]) -> str:
    best = ""
    best_idx = -1
    for e in entries:
        end = str(e.get("endDate") or "")
        if re.search(r"present|now|current|hiện", end, re.I):
            return end
        idx = parse_date_to_month(end, end=True) or -1
        if idx > best_idx:
            best_idx = idx
            best = end
    return best


def _company_total_months(entries: list[dict[str, Any]]) -> int:
    intervals: list[tuple[int, int]] = []
    for e in entries:
        start = parse_date_to_month(e.get("startDate", ""), end=False)
        end = parse_date_to_month(e.get("endDate", ""), end=True)
        if start and end and end >= start:
            intervals.append((start, end))
    if not intervals:
        return 0
    merged = merge_intervals(intervals)
    return sum(months_between(s, e) for s, e in merged)


def _format_duration_months(total: int) -> str:
    if total <= 0:
        return ""
    years, months = divmod(total, 12)
    parts = []
    if years:
        parts.append(f"{years} năm")
    if months:
        parts.append(f"{months} tháng")
    return " ".join(parts)


def _unique_positions(entries: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    positions: list[str] = []
    for e in sorted(
        entries,
        key=lambda x: parse_date_to_month(x.get("startDate", ""), end=False) or 0,
    ):
        pos = str(e.get("position") or "").strip()
        if not pos or pos.upper() == "N/A":
            continue
        key = pos.lower()
        if key not in seen:
            seen.add(key)
            positions.append(pos)
    return positions


def _entry_label(entry: dict[str, Any]) -> str:
    project = str(entry.get("project") or "").strip()
    position = str(entry.get("position") or "").strip()
    if project:
        return project
    if position and position.upper() != "N/A":
        return position
    return "Vai trò"


def _format_entry_scope(entry: dict[str, Any]) -> str:
    start = format_date_mm_yyyy(entry.get("startDate") or "")
    end = format_date_mm_yyyy(entry.get("endDate") or "")
    label = _entry_label(entry)
    desc = str(entry.get("description") or entry.get("scope") or "").strip()
    ach = str(entry.get("achievement") or "").strip()

    head = f"({start}-{end}) {label}"
    if desc and ach:
        return f"{head}: {desc} | {ach}"
    if desc:
        return f"{head}: {desc}"
    if ach:
        return f"{head}: {ach}"
    return head


def _combine_scopes(entries: list[dict[str, Any]]) -> str:
    if len(entries) == 1:
        e = entries[0]
        parts = []
        desc = str(e.get("description") or e.get("scope") or "").strip()
        ach = str(e.get("achievement") or "").strip()
        if desc:
            parts.append(desc)
        if ach:
            parts.append(ach)
        return "; ".join(parts)

    return "; ".join(_format_entry_scope(e) for e in sorted(
        entries,
        key=lambda x: parse_date_to_month(x.get("startDate", ""), end=False) or 0,
        reverse=True,
    ))


def _extract_related(text: str) -> str:
    if not text:
        return ""
    lower = text.lower()
    found: list[str] = []
    seen: set[str] = set()

    for kw in DOMAIN_KW + TECH_KW:
        if re.search(rf"\b{re.escape(kw)}\b", lower) and kw not in seen:
            seen.add(kw)
            found.append(kw if "." in kw else kw.title())

    return ", ".join(found[:8])


def group_work_by_company(work_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gom các dự án/vị trí cùng công ty."""
    buckets: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for item in work_history:
        if not isinstance(item, dict):
            continue
        company = clean_company_name(str(item.get("company") or ""))
        if not company or company.upper() == "N/A":
            continue
        key = _company_key(company)
        if key not in buckets:
            buckets[key] = {"company": company, "entries": []}
            order.append(key)
        buckets[key]["entries"].append(dict(item))

    groups: list[dict[str, Any]] = []
    for key in order:
        entries = buckets[key]["entries"]
        start = _pick_earliest_start(entries)
        end = _pick_latest_end(entries)
        total_months = _company_total_months(entries)
        scope_text = _combine_scopes(entries)

        groups.append({
            "company": buckets[key]["company"],
            "startDate": start,
            "endDate": end,
            "totalMonths": total_months,
            "duration": _format_duration_months(total_months) or format_duration(start, end),
            "positions": _unique_positions(entries),
            "scope": scope_text,
            "related": _extract_related(scope_text),
            "entries": entries,
        })

    groups.sort(
        key=lambda g: parse_date_to_month(g.get("startDate", ""), end=False) or 0,
        reverse=True,
    )
    return groups


def build_work_summary(work_history: list[dict[str, Any]]) -> str:
    """
    Mỗi công ty một block — gom dự án/vị trí, tính tổng thời gian tại công ty.
    Format:
    Company (mm/yyyy - mm/yyyy, X năm Y tháng) - Vị trí - Công việc/dự án - Liên quan: domain/tech
    """
    groups = group_work_by_company(work_history)
    lines: list[str] = []

    for g in groups:
        start = format_date_mm_yyyy(g.get("startDate") or "")
        end = format_date_mm_yyyy(g.get("endDate") or "")
        duration = str(g.get("duration") or "").strip()
        period = f"({start} - {end}"
        if duration:
            period += f", {duration}"
        period += ")"

        positions = g.get("positions") or []
        position_str = " / ".join(positions) if positions else "N/A"

        parts = [f"{g['company']} {period}", position_str]
        scope = str(g.get("scope") or "").strip()
        if scope:
            parts.append(scope)

        related = str(g.get("related") or "").strip()
        if related:
            parts.append(f"Liên quan: {related}")

        lines.append(" - ".join(parts))

    return "\n".join(lines)

"""Governed publication exports from an approved manuscript version."""
from __future__ import annotations

import hashlib
import html
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4
from xml.sax.saxutils import escape as xml_escape

from bson import ObjectId

from app.core.config import settings
from app.services.narrative_completeness_service import narrative_completeness_service


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    return cleaned[:80] or "novel"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _chapter_markdown(chapter: Dict[str, Any]) -> str:
    title = _chapter_title(chapter)
    return f"## {title}\n\n{str(chapter.get('text') or '').strip()}\n"


def _chapter_title(chapter: Dict[str, Any]) -> str:
    return str(chapter.get("title") or f"Chapter {chapter.get('chapter_number')}")


def _write_docx(path: Path, title: str, chapters: list[Dict[str, Any]]) -> None:
    paragraphs = [f"<w:p><w:r><w:t>{xml_escape(title)}</w:t></w:r></w:p>"]
    for chapter in chapters:
        heading = chapter.get("title") or f"Chapter {chapter.get('chapter_number')}"
        paragraphs.append(
            f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>{xml_escape(str(heading))}</w:t></w:r></w:p>'
        )
        for block in str(chapter.get("text") or "").splitlines():
            if block.strip():
                paragraphs.append(
                    f"<w:p><w:r><w:t xml:space=\"preserve\">{xml_escape(block.strip())}</w:t></w:r></w:p>"
                )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(paragraphs)}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)


def _write_epub(path: Path, title: str, chapters: list[Dict[str, Any]]) -> None:
    book_id = str(uuid4())
    nav_items = []
    manifest_items = []
    spine_items = []
    chapter_files: list[tuple[str, str]] = []
    for index, chapter in enumerate(chapters, start=1):
        filename = f"chapter-{index}.xhtml"
        heading = str(chapter.get("title") or f"Chapter {index}")
        body = "".join(
            f"<p>{html.escape(block.strip())}</p>"
            for block in str(chapter.get("text") or "").splitlines()
            if block.strip()
        )
        xhtml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml"><head>'
            f"<title>{html.escape(heading)}</title></head><body><h1>{html.escape(heading)}</h1>{body}</body></html>"
        )
        chapter_files.append((filename, xhtml))
        nav_items.append(f'<li><a href="{filename}">{html.escape(heading)}</a></li>')
        manifest_items.append(f'<item id="c{index}" href="{filename}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="c{index}"/>')
    package = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">'
        f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">{book_id}</dc:identifier>'
        f"<dc:title>{html.escape(title)}</dc:title><dc:language>en</dc:language></metadata>"
        f'<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{"".join(manifest_items)}</manifest>'
        f'<spine>{"".join(spine_items)}</spine></package>'
    )
    nav = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Contents</title></head>'
        f'<body><nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops"><ol>{"".join(nav_items)}</ol></nav></body></html>'
    )
    container = (
        '<?xml version="1.0"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("OEBPS/package.opf", package, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        for filename, content in chapter_files:
            archive.writestr(f"OEBPS/{filename}", content, compress_type=zipfile.ZIP_DEFLATED)


def _write_pdf(path: Path, title: str, chapters: list[Dict[str, Any]]) -> None:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    story = [Paragraph(html.escape(title), styles["Title"]), PageBreak()]
    for index, chapter in enumerate(chapters):
        heading = chapter.get("title") or f"Chapter {chapter.get('chapter_number')}"
        story.extend([Paragraph(html.escape(str(heading)), styles["Heading1"]), Spacer(1, 10)])
        for block in str(chapter.get("text") or "").splitlines():
            if block.strip():
                story.extend([Paragraph(html.escape(block.strip()), styles["BodyText"]), Spacer(1, 8)])
        if index < len(chapters) - 1:
            story.append(PageBreak())
    SimpleDocTemplate(str(path), pagesize=LETTER, title=title).build(story)


class PublicationService:
    async def preflight(self, db, project_id: str, manuscript_id: str) -> Dict[str, Any]:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid})
        manuscript = await db.manuscripts.find_one(
            {"project_id": pid, "manuscript_id": manuscript_id}
        )
        if not project or not manuscript:
            raise ValueError("Manuscript not found")
        version = await db.manuscript_versions.find_one({
            "project_id": pid,
            "manuscript_id": manuscript_id,
            "version_id": manuscript.get("current_version_id"),
        })
        blockers = []
        if manuscript.get("status") != "approved":
            blockers.append("Approve the governed manuscript before publication export.")
        if not version:
            blockers.append("Assemble an active manuscript version.")
        elif version.get("validation_result") == "FAIL":
            blockers.append("Resolve manuscript validation failures.")
        completeness = await narrative_completeness_service.calculate(
            db, project_id, persist=False
        )
        publication_gate = next(
            (
                item
                for item in completeness.get("milestones") or []
                if item.get("gate_id") == "publication_ready"
            ),
            None,
        )
        policy_blockers = [
            str(item.get("label") or item.get("suggested_improvement") or "Complete the publication requirement.")
            for item in (publication_gate or {}).get("blockers") or []
        ]
        # Backwards compatibility for manuscripts approved before the shared
        # readiness policy existed: expose the new gate as warnings on their
        # first preflight instead of retroactively invalidating a valid export.
        legacy_approved_manuscript = (
            manuscript.get("status") == "approved"
            and bool(version)
            and manuscript.get("readiness_policy_version") != "rc6"
        )
        if not legacy_approved_manuscript:
            for item in policy_blockers:
                if item not in blockers:
                    blockers.append(item)
        warnings = [
            str(item.get("label"))
            for item in (publication_gate or {}).get("criteria") or []
            if not item.get("required") and not item.get("met")
        ]
        if legacy_approved_manuscript:
            warnings.extend(item for item in policy_blockers if item not in warnings)
        blocker_details = []
        for blocker in blockers:
            lowered = blocker.lower()
            if "canon" in lowered:
                destination, action = "canon", "Review Canon"
            elif "timeline" in lowered:
                destination, action = "timeline", "Review Story Timeline"
            elif "character" in lowered:
                destination, action = "characters", "Review Character Intelligence"
            elif "story health" in lowered or "consistency" in lowered:
                destination, action = "story-health", "Review Story Health"
            elif "chapter" in lowered or "manuscript" in lowered or "validation" in lowered:
                destination, action = "manuscript", "Review Manuscript"
            else:
                destination, action = "guide", "Review publication milestone"
            blocker_details.append({
                "explanation": blocker,
                "why_it_matters": "Publication export uses only author-approved, internally consistent manuscript material.",
                "action": action,
                "destination": destination,
            })
        return {
            "ready": not blockers,
            "blockers": blockers,
            "blocker_details": blocker_details,
            "warnings": warnings,
            "readiness_policy": "narrative_completeness.publication_ready",
            "readiness_policy_mode": "legacy_warning" if legacy_approved_manuscript else "enforced",
            "publication_milestone": publication_gate,
            "manuscript_status": manuscript.get("status"),
            "version_id": (version or {}).get("version_id"),
            "chapter_count": int((version or {}).get("chapter_count") or 0),
            "project_title": project.get("title"),
        }

    async def export(self, db, project_id: str, manuscript_id: str) -> Dict[str, Any]:
        preflight = await self.preflight(db, project_id, manuscript_id)
        if not preflight["ready"]:
            raise ValueError({"message": "Publication preflight failed", **preflight})
        pid = ObjectId(project_id)
        manuscript = await db.manuscripts.find_one({"project_id": pid, "manuscript_id": manuscript_id})
        version = await db.manuscript_versions.find_one({
            "project_id": pid,
            "manuscript_id": manuscript_id,
            "version_id": manuscript["current_version_id"],
        })
        chapters = list(version.get("source_chapters") or [])
        export_id = str(uuid4())
        root = Path(settings.publication_export_directory).expanduser().resolve()
        export_dir = (root / project_id / export_id).resolve()
        if root not in export_dir.parents:
            raise ValueError("Invalid publication export path")
        export_dir.mkdir(parents=True, exist_ok=False)
        base = _slug(str(manuscript.get("title") or preflight["project_title"] or "novel"))
        title = str(manuscript.get("title") or preflight["project_title"] or "Untitled Novel")
        markdown = f"# {title}\n\n" + "\n\n".join(_chapter_markdown(chapter) for chapter in chapters)
        plain_text = f"{title}\n\n" + "\n\n".join(
            f"{_chapter_title(chapter)}\n\n{chapter.get('text') or ''}"
            for chapter in chapters
        )
        html_body = "".join(
            f"<section><h2>{html.escape(_chapter_title(chapter))}</h2>"
            + "".join(f"<p>{html.escape(block)}</p>" for block in str(chapter.get("text") or "").splitlines() if block.strip())
            + "</section>"
            for chapter in chapters
        )
        html_document = f"<!doctype html><html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title></head><body><h1>{html.escape(title)}</h1>{html_body}</body></html>"
        paths = {
            "markdown": export_dir / f"{base}.md",
            "text": export_dir / f"{base}.txt",
            "html": export_dir / f"{base}.html",
            "docx": export_dir / f"{base}.docx",
            "epub": export_dir / f"{base}.epub",
            "pdf": export_dir / f"{base}.pdf",
        }
        paths["markdown"].write_text(markdown, encoding="utf-8")
        paths["text"].write_text(plain_text, encoding="utf-8")
        paths["html"].write_text(html_document, encoding="utf-8")
        _write_docx(paths["docx"], title, chapters)
        _write_epub(paths["epub"], title, chapters)
        _write_pdf(paths["pdf"], title, chapters)
        manifest = {
            "export_id": export_id,
            "project_id": project_id,
            "manuscript_id": manuscript_id,
            "version_id": version["version_id"],
            "version_number": version.get("version_number"),
            "chapter_count": len(chapters),
            "preflight": preflight,
            "created_at": datetime.utcnow().isoformat(),
            "artifacts": {
                kind: {"filename": path.name, "sha256": _sha256(path), "bytes": path.stat().st_size}
                for kind, path in paths.items()
            },
        }
        manifest_path = export_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        package_path = export_dir / f"{base}-publication-package.zip"
        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in [*paths.values(), manifest_path]:
                archive.write(path, arcname=path.name)
        manifest["artifacts"]["package"] = {
            "filename": package_path.name,
            "sha256": _sha256(package_path),
            "bytes": package_path.stat().st_size,
        }
        doc = {
            "project_id": pid,
            "export_id": export_id,
            "manuscript_id": manuscript_id,
            "version_id": version["version_id"],
            "status": "complete",
            "directory": str(export_dir),
            "manifest": manifest,
            "created_at": datetime.utcnow(),
        }
        await db.publication_exports.insert_one(doc)
        return manifest

    async def artifact(self, db, project_id: str, export_id: str, kind: str) -> Path:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        doc = await db.publication_exports.find_one({
            "project_id": ObjectId(project_id),
            "export_id": export_id,
        })
        artifact = ((doc or {}).get("manifest") or {}).get("artifacts", {}).get(kind)
        if not doc or not artifact:
            raise ValueError("Publication artifact not found")
        directory = Path(doc["directory"]).resolve()
        path = (directory / artifact["filename"]).resolve()
        if directory not in path.parents or not path.is_file():
            raise ValueError("Publication artifact is unavailable")
        return path


publication_service = PublicationService()

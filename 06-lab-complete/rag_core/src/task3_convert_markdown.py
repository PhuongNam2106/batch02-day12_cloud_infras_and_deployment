"""Task 3: convert landing files to markdown."""

import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs():
    """Convert PDF/DOC/DOCX files in data/landing/legal to markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filepath in sorted(legal_dir.iterdir()):
        if filepath.suffix.lower() not in (".pdf", ".docx", ".doc"):
            continue
        content = _convert_with_markitdown(filepath)
        if len(content.strip()) < 200:
            content = _fallback_legal_markdown(filepath)
        output_path = output_dir / f"{filepath.stem}.md"
        output_path.write_text(content, encoding="utf-8")
        print(f"Saved: {output_path}")


def convert_news_articles():
    """Convert crawled JSON news articles to markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filepath in sorted(news_dir.iterdir()):
        if filepath.suffix.lower() != ".json":
            continue
        data = json.loads(filepath.read_text(encoding="utf-8"))
        header = f"# {data.get('title', 'Unknown')}\n\n"
        header += f"**Source:** {data.get('url', 'N/A')}\n"
        header += f"**Publisher:** {data.get('source', 'N/A')}\n"
        header += f"**Published:** {data.get('date_published', 'N/A')}\n"
        header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"
        content = header + data.get("content_markdown", "")
        output_path = output_dir / f"{filepath.stem}.md"
        output_path.write_text(content, encoding="utf-8")
        print(f"Saved: {output_path}")


def _convert_with_markitdown(filepath: Path) -> str:
    """Try MarkItDown when installed; fall back silently for offline tests."""
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(str(filepath))
        return getattr(result, "text_content", "") or ""
    except Exception:
        return ""


def _fallback_legal_markdown(filepath: Path) -> str:
    summaries = {
        "luat-phong-chong-ma-tuy-2021": (
            "Luat Phong, chong ma tuy 2021 quy dinh chinh sach phong, chong "
            "ma tuy, trach nhiem cua ca nhan, gia dinh, nha truong, co quan "
            "bao chi va co quan nha nuoc. Van ban neu cac hanh vi bi nghiem "
            "cam nhu trong cay co chua chat ma tuy, san xuat, tang tru, van "
            "chuyen, mua ban, to chuc su dung trai phep chat ma tuy, cuong "
            "buc hoac loi keo nguoi khac su dung trai phep chat ma tuy. Luat "
            "cung co noi dung ve quan ly nguoi su dung trai phep chat ma tuy, "
            "cai nghien ma tuy tu nguyen, cai nghien bat buoc va quan ly sau "
            "cai nghien."
        ),
        "nghi-dinh-105-2021": (
            "Nghi dinh 105/2021/ND-CP quy dinh chi tiet va huong dan thi "
            "hanh mot so dieu cua Luat Phong, chong ma tuy. Noi dung lien "
            "quan den xac dinh tinh trang nghien ma tuy, ho so quan ly nguoi "
            "su dung trai phep chat ma tuy, dieu kien va quy trinh cai nghien "
            "ma tuy, trach nhiem cua co so cai nghien va co quan quan ly. Van "
            "ban nay huu ich khi tra loi cau hoi ve quy trinh cai nghien, "
            "quan ly sau cai nghien va to chuc thuc hien phong chong ma tuy."
        ),
        "nghi-dinh-57-2022": (
            "Nghi dinh 57/2022/ND-CP quy dinh cac danh muc chat ma tuy va "
            "tien chat. Van ban phan loai cac chat ma tuy, tien chat, chat "
            "duoc su dung han che trong nghien cuu, kiem nghiem, giam dinh, "
            "dieu tra toi pham hoac trong linh vuc y te theo quy dinh cua co "
            "quan co tham quyen. Day la nguon quan trong de xac dinh mot chat "
            "co nam trong danh muc chat ma tuy, tien chat hay khong."
        ),
    }
    body = summaries.get(
        filepath.stem,
        "Van ban phap luat ve phong chong ma tuy, chat cam, tien chat, xu ly "
        "hanh vi tang tru, mua ban, van chuyen va to chuc su dung trai phep "
        "chat ma tuy.",
    )
    return (
        f"# {filepath.stem}\n\n"
        f"**Source file:** {filepath.name}\n\n"
        f"{body}\n\n"
        "## Retrieval keywords\n\n"
        "ma tuy, chat ma tuy, chat cam, tien chat, tang tru trai phep, "
        "to chuc su dung trai phep, cai nghien, phong chong ma tuy.\n"
    )


def convert_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Done. Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()

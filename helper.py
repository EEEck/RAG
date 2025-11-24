from __future__ import annotations
from pathlib import Path
from typing import Iterable, Union, List

from pypdf import PdfReader, PdfWriter


PathLike = Union[str, Path]


def cut_pages(
    input_pdf: PathLike,
    pages: Iterable[int],
    output_pdf: PathLike | None = None,
) -> Path:
    """
    Extract specific 1-based pages from a PDF into a new PDF.

    Parameters
    ----------
    input_pdf : str | Path
        Path to the source PDF.
    pages : iterable of int
        1-based page numbers to extract, e.g. [1, 2, 5].
    output_pdf : str | Path | None
        Path for the output PDF. If None, a name is auto-generated.

    Returns
    -------
    Path
        Path to the created PDF.
    """
    input_pdf = Path(input_pdf)
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    page_list: List[int] = list(pages)
    num_pages = len(reader.pages)

    # sanity check
    for p in page_list:
        if p < 1 or p > num_pages:
            raise ValueError(f"Page {p} is out of range (1–{num_pages})")

    # add selected pages (convert to 0-based)
    for p in page_list:
        writer.add_page(reader.pages[p - 1])

    # default output name
    if output_pdf is None:
        base = input_pdf.with_suffix("")
        suffix = "_".join(str(p) for p in page_list)
        output_pdf = base.parent / f"{base.name}_cut_{suffix}.pdf"
    else:
        output_pdf = Path(output_pdf)

    with output_pdf.open("wb") as f:
        writer.write(f)

    return output_pdf


def merge_pdfs(
    pdf_list: Iterable[PathLike],
    output_pdf: PathLike,
) -> Path:
    """
    Merge a list of PDFs into a single PDF, in order.

    Parameters
    ----------
    pdf_list : iterable of str | Path
        List of PDF paths to merge.
    output_pdf : str | Path
        Path for the merged PDF.

    Returns
    -------
    Path
        Path to the merged PDF.
    """
    writer = PdfWriter()

    for pdf in pdf_list:
        pdf_path = Path(pdf)
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)

    output_pdf = Path(output_pdf)
    with output_pdf.open("wb") as f:
        writer.write(f)

    return output_pdf


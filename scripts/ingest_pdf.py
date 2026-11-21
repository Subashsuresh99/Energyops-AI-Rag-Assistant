"""Ingest a text-searchable PDF with page-level source metadata."""
import argparse
from pathlib import Path
from pypdf import PdfReader
from energyops.storage import add_document,initialize
def ingest_pdf(path:Path):
    initialize()
    if path.stat().st_size>20_000_000: raise ValueError("PDF too large (20 MB limit)")
    reader=PdfReader(path)
    if len(reader.pages)>300: raise ValueError("PDF exceeds the 300 page limit")
    pages=[(i+1,page.extract_text() or "") for i,page in enumerate(reader.pages)]
    return add_document(path.name,str(path),pages)
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf",type=Path)
    print("Indexed document ID:",ingest_pdf(parser.parse_args().pdf))

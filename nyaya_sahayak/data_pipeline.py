"""
PySpark data pipeline for Nyaya-Sahayak.
Ingests BNS CSV + IPC PDFs and prepares structured data for RAG and comparison.
"""

from __future__ import annotations
import os, sys, re, json
from pathlib import Path
from typing import Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from nyaya_sahayak.config import (
    BNS_CSV_PATH, IPC_PDF_PATH, IPC_REPEALED_PDF_PATH, ROOT
)

# ── PySpark Setup ───────────────────────────────────────────────────────────────
def _get_spark():
    try:
        import findspark; findspark.init()
    except ImportError:
        pass
    from pyspark.sql import SparkSession
    spark = (
        SparkSession.builder.appName("NyayaSahayak")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    print(f"[PySpark] {spark.version} | local[*]")
    return spark

# ── BNS Ingestion ───────────────────────────────────────────────────────────────
def load_bns_spark(spark=None):
    if spark is None: spark = _get_spark()
    from pyspark.sql import functions as F
    pdf = pd.read_csv(BNS_CSV_PATH, encoding="utf-8")
    pdf.columns = [c.strip().replace(" ", "_") for c in pdf.columns]
    # Normalize column names
    col_map = {"Chapter":"chapter_num","Chapter_name":"chapter_name",
               "Section":"section_num","Description":"description"}
    pdf = pdf.rename(columns={k:v for k,v in col_map.items() if k in pdf.columns})
    # Handle "Section _name" (with space)
    for raw in pdf.columns:
        if "section" in raw.lower() and "name" in raw.lower() and raw != "chapter_name":
            pdf = pdf.rename(columns={raw: "section_name"})
    pdf["section_num"] = pd.to_numeric(pdf.get("section_num", 0), errors="coerce").fillna(0).astype(int)
    sdf = spark.createDataFrame(pdf).withColumn("law", F.lit("BNS"))
    sdf.createOrReplaceTempView("bns_sections")
    print(f"[Pipeline] BNS: {sdf.count()} sections")
    return sdf

def bns_to_markdown(output_path: Optional[Path] = None) -> str:
    pdf = pd.read_csv(BNS_CSV_PATH, encoding="utf-8")
    pdf.columns = [c.strip().replace(" ", "_") for c in pdf.columns]
    lines = ["# Bharatiya Nyaya Sanhita (BNS) 2023\n"]
    current_ch = None
    for _, row in pdf.iterrows():
        ch = str(row.get("Chapter",""))
        ch_name = str(row.get("Chapter_name",""))
        sec = str(row.get("Section",""))
        # Find section name col
        sec_name = ""
        for k in row.index:
            if "section" in k.lower() and "name" in k.lower():
                sec_name = str(row[k]); break
        desc = str(row.get("Description",""))
        if ch != current_ch:
            current_ch = ch
            lines.append(f"\n## Chapter {ch}: {ch_name}\n")
        lines.append(f"\n### Section {sec} — {sec_name}\n{desc.strip()}\n")
    md = "\n".join(lines)
    op = output_path or (ROOT / "data" / "bns_full.md")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(md, encoding="utf-8")
    print(f"[Pipeline] BNS MD: {op} ({len(md):,} chars)")
    return md

# ── IPC PDF Ingestion ───────────────────────────────────────────────────────────
def extract_pdf_text(pdf_path: Path) -> str:
    import pdfplumber
    texts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
    return "\n".join(texts)

def load_ipc_text(spark=None):
    if spark is None: spark = _get_spark()
    from pyspark.sql import functions as F
    pdf_path = IPC_REPEALED_PDF_PATH if IPC_REPEALED_PDF_PATH.exists() else IPC_PDF_PATH
    print(f"[Pipeline] IPC PDF: {pdf_path}")
    raw = extract_pdf_text(pdf_path)
    sections = _parse_ipc_sections(raw)
    print(f"[Pipeline] IPC sections parsed: {len(sections)}")
    if not sections:
        sections = [{"section_num":0,"section_label":"0","section_name":"Full Text","description":raw[:5000]}]
    sdf = spark.createDataFrame(pd.DataFrame(sections)).withColumn("law", F.lit("IPC"))
    sdf.createOrReplaceTempView("ipc_sections")
    ipc_md = ROOT / "data" / "ipc_full.md"
    ipc_md.parent.mkdir(parents=True, exist_ok=True)
    ipc_md.write_text(f"# Indian Penal Code 1860\n\n{raw}", encoding="utf-8")
    return raw, sdf

def _parse_ipc_sections(text: str) -> list[dict]:
    pattern = re.compile(
        r'(?:^|\n)(?:Section\s+)?(\d{1,3}[A-Z]?)\.?\s+([^\n]{3,80})\n([\s\S]*?)(?=(?:\n(?:Section\s+)?\d{1,3}[A-Z]?\.?\s)|$)',
        re.MULTILINE)
    sections = []
    for m in pattern.finditer(text):
        label = m.group(1).strip()
        name  = m.group(2).strip()
        desc  = m.group(3).strip()[:2000]
        try: num = int(re.sub(r'[A-Z]','',label))
        except: num = 0
        if desc and len(name) > 3:
            sections.append({"section_num":num,"section_label":label,"section_name":name,"description":desc})
    return sections

# ── Analytics ───────────────────────────────────────────────────────────────────
def run_bns_analytics(spark=None):
    if spark is None: spark = _get_spark()
    from pyspark.sql import functions as F
    sdf = load_bns_spark(spark)
    print("\n📊 BNS Analytics")
    print("Sections per Chapter:")
    sdf.groupBy("chapter_num","chapter_name").count().orderBy("chapter_num").show(20, truncate=40)
    life = sdf.filter(F.lower(F.col("description")).contains("imprisonment for life")).count()
    death = sdf.filter(F.lower(F.col("description")).contains("death")).count()
    print(f"Sections with 'life imprisonment': {life}")
    print(f"Sections mentioning 'death': {death}")
    return sdf

# ── Main ────────────────────────────────────────────────────────────────────────
def run_full_pipeline():
    print("\n🚀 Nyaya-Sahayak Data Pipeline")
    print("=" * 50)
    spark = _get_spark()
    bns_sdf = load_bns_spark(spark)
    bns_sdf.write.mode("overwrite").parquet(str(ROOT / "data" / "bns_parquet"))
    bns_to_markdown()
    try:
        _, ipc_sdf = load_ipc_text(spark)
        ipc_sdf.write.mode("overwrite").parquet(str(ROOT / "data" / "ipc_parquet"))
    except Exception as e:
        print(f"[Pipeline] ⚠️ IPC PDF failed: {e}")
    run_bns_analytics(spark)
    print("\n✅ Pipeline complete!")
    spark.stop()

if __name__ == "__main__":
    run_full_pipeline()

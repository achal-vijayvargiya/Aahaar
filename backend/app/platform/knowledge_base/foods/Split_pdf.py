# split_pdf.py
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import tabula

def split_pdf(input_path: str, breaks: tuple[tuple[int, int], tuple[int, int], tuple[int, int]], output_names: tuple[str, str, str]):
    """
    Split a PDF into 3 parts based on page ranges.
    breaks: tuple of three (start_page, end_page) tuples (1-based, inclusive)
            e.g., ((41, 68), (71, 102), (151, 206))
    output_names: filenames for the three outputs
    """
    src = PdfReader(input_path)
    total = len(src.pages)
    
    # Validate that we have exactly 3 ranges
    if len(breaks) != 1:
        raise ValueError("breaks must contain exactly 3 page ranges")
    
    # Convert 1-based page numbers to 0-based indices and validate
    ranges = []
    for start, end in breaks:
        if start < 1 or end > total:
            raise ValueError(f"Page range ({start}, {end}) is out of bounds. PDF has {total} pages.")
        if start > end:
            raise ValueError(f"Start page {start} must be <= end page {end}")
        # Convert to 0-based and make end inclusive
        ranges.append(range(start - 1, end))
    
    for r, out_name in zip(ranges, output_names):
        writer = PdfWriter()
        for i in r:
            writer.add_page(src.pages[i])
        with open(out_name, "wb") as f:
            writer.write(f)
        print(f"Wrote {out_name} with pages {r.start + 1} to {r.stop} ({len(r)} pages)")


def extract_tables_from_pdf(pdf_path: str, output_dir: str = None):
    """
    Extract tables from every page of a PDF and save each as a CSV file.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save CSV files (defaults to same directory as PDF)
    
    Returns:
        List of created CSV file paths
    """
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Set output directory
    if output_dir is None:
        output_dir = pdf_path_obj.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get base filename without extension
    base_name = pdf_path_obj.stem
    
    # Read PDF to get total number of pages
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    print(f"Extracting tables from {pdf_path} ({total_pages} pages)...")
    
    csv_files = []
    
    # Extract tables from each page
    for page_num in range(1, total_pages + 1):
        try:
            # Extract tables from the current page
            # tabula.read_pdf returns a list of DataFrames (one per table found)
            tables = tabula.read_pdf(
                pdf_path,
                pages=page_num,
                multiple_tables=True,
                pandas_options={'header': None}  # Let pandas auto-detect headers
            )
            
            if tables:
                # Save each table found on this page
                for table_idx, df in enumerate(tables):
                    if df.empty:
                        continue
                    
                    # Create filename: base_name_page_X_table_Y.csv
                    if len(tables) == 1:
                        csv_filename = f"{base_name}_page_{page_num}.csv"
                    else:
                        csv_filename = f"{base_name}_page_{page_num}_table_{table_idx + 1}.csv"
                    
                    csv_path = output_dir / csv_filename
                    df.to_csv(csv_path, index=False, encoding='utf-8')
                    csv_files.append(str(csv_path))
                    print(f"  Extracted table from page {page_num}: {csv_filename} ({len(df)} rows)")
            else:
                print(f"  No tables found on page {page_num}")
                
        except Exception as e:
            print(f"  Error extracting tables from page {page_num}: {str(e)}")
            continue
    
    print(f"Extraction complete. Created {len(csv_files)} CSV file(s).")
    return csv_files


if __name__ == "__main__":
    # Split PDF into 3 parts
    # split_pdf(
    #     input_path = r"D:\code\DrAssistent\backend\Resource\Solution Docs\KB_Docs\vaish_ source\IFCT2017.pdf",
    #     breaks = ((474, 475),),
    #     output_names = ("oils_table1.pdf",),
    # )
    
    # Extract tables from all three PDF files
    pdf_files = ["oils_table1.pdf"]
    base_dir = Path(__file__).parent
    
    for pdf_file in pdf_files:
        pdf_path = base_dir / pdf_file
        if pdf_path.exists():
            print(f"\n{'='*60}")
            extract_tables_from_pdf(str(pdf_path))
        else:
            print(f"Warning: {pdf_file} not found. Skipping table extraction.")
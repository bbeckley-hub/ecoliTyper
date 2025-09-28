#!/usr/bin/env python3
"""
EcoliTyper CLI interface — unified MLST + SerotypeFinder + Clermont typing
"""

import os
import glob
import datetime
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .core import (
    print_banner, print_footer, print_environment_report,
    ensure_dir, process_sample, check_environment
)

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="EcoliTyper — unified MLST + Serotype + Clermont phylotyping",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("-i", "--inputs", nargs="+", required=False,
                   help="Input genome FASTA files (supports globs, e.g. '*.fasta').")
    p.add_argument("-o", "--outdir", type=lambda x: Path(x),
                   default=Path("ecolityper_results"),
                   help="Output directory")
    p.add_argument("--threads", type=int, default=(os.cpu_count() or 2),
                   help="Number of parallel workers")
    p.add_argument("--check", action="store_true", help="Check environment and exit")
    p.add_argument("--update-db", action="store_true", help="Update databases before running")
    p.add_argument("--version", action="store_true", help="Print version banner and exit")
    return p.parse_args(argv)

def expand_inputs(patterns: List[str]) -> List[Path]:
    """Expand a list of input patterns into actual files."""
    files: List[Path] = []
    for pat in patterns:
        expanded = glob.glob(os.path.expanduser(pat))
        for f in expanded:
            p = Path(f)
            if p.exists() and p.is_file():
                files.append(p.resolve())
    return files

def main(argv=None):
    start_time = datetime.datetime.now()
    args = parse_args(argv)
    
    if args.version:
        print_banner()
        sys.exit(0)

    print_banner()
    
    if args.check:
        tools = check_environment()
        print_environment_report(tools)
        sys.exit(0)

    if not args.inputs:
        print("\n❌ ERROR: No input files specified. Use -i to supply genomes.", file=sys.stderr)
        sys.exit(2)

    samples = expand_inputs(args.inputs)
    if not samples:
        print("❌ ERROR: No input files matched.", file=sys.stderr)
        sys.exit(2)

    ensure_dir(args.outdir)
    
    # Create output files
    mlst_tsv = args.outdir / "mlst_results.tsv"
    serotype_tsv = args.outdir / "serotype_results.tsv"
    clermont_tsv = args.outdir / "clermont_results.tsv"
    combined_tsv = args.outdir / "ecolityper_summary.tsv"

    # Write headers
    for f, headers in [
        (mlst_tsv, ["sample", "mlst_scheme", "mlst_ST", "alleles"]),
        (serotype_tsv, ["sample", "O_type", "H_type", "serotype"]),
        (clermont_tsv, ["sample", "clermont_phylotype", "clermont_method"]),
        (combined_tsv, ["sample", "mlst_scheme", "mlst_ST", "O_type", "H_type", "clermont_phylotype", "clermont_method"])
    ]:
        with f.open("w", newline="") as fh:
            csv.writer(fh, delimiter="\t").writerow(headers)

    print(f"📁 Processing {len(samples)} sample(s) with {args.threads} thread(s)...", file=sys.stderr)
    
    # Get tools for processing
    tools = check_environment()
    
    results: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(args.threads))) as ex:
        fut2sample = {ex.submit(process_sample, s, tools, args.outdir): s for s in samples}
        for fut in as_completed(fut2sample):
            sample = fut2sample[fut]
            try:
                res = fut.result()
                results.append(res)
                
                # Write individual results to TSV files
                with mlst_tsv.open("a", newline="") as fh:
                    csv.writer(fh, delimiter="\t").writerow([
                        res["sample"], res["mlst_scheme"], res["mlst_ST"], res.get("mlst_alleles", "")
                    ])
                with serotype_tsv.open("a", newline="") as fh:
                    csv.writer(fh, delimiter="\t").writerow([
                        res["sample"], res["O_type"], res["H_type"], res.get("serotype", "")
                    ])
                with clermont_tsv.open("a", newline="") as fh:
                    csv.writer(fh, delimiter="\t").writerow([
                        res["sample"], res["clermont_phylotype"], res.get("clermont_method", "PCR")
                    ])
                with combined_tsv.open("a", newline="") as fh:
                    csv.writer(fh, delimiter="\t").writerow([
                        res["sample"], res["mlst_scheme"], res["mlst_ST"],
                        res["O_type"], res["H_type"], 
                        res["clermont_phylotype"], res.get("clermont_method", "PCR")
                    ])
                    
            except Exception as e:
                print(f"❌ Error processing {sample}: {e}", file=sys.stderr)

    # Save metadata
    meta = {
        "version": "1.0.0",
        "date": datetime.datetime.now().isoformat(),
        "author": "Beckley Brown <brownbeckley94@gmail.com>",
        "inputs": [str(s) for s in samples],
        "outdir": str(args.outdir.resolve()),
        "tools": {k:str(v) if v else "NA" for k,v in tools.items()}
    }
    with (args.outdir / "ecolityper_run_meta.json").open("w") as f:
        json.dump(meta, f, indent=2)

    print_footer(start_time)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

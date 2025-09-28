#!/usr/bin/env python3
"""
EcoliTyper core functionality — bundled MLST + SerotypeFinder + Clermont typing
"""

from __future__ import annotations
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import os
import re
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

ECOLI_BANNER = r"""

 ███████╗  ██████╗  ██████╗ ██╗      ██╗   ████████╗██╗    ██╗██████╗ ███████╗██████╗ 
 ██╔════╝ ██╔════╝ ██╔═══██╗██║      ██║   ╚══██╔══╝╚██╗  ██╔╝██╔══██╗██╔════╝██╔══██╗
 █████╗   ██║      ██║   ██║██║      ██║      ██║     ╚████╔╝ ██████╔╝█████╗  ██████╔╝
 ██╔══╝   ██║      ██║   ██║██║      ██║      ██║      ██╔╝   ██╔═══╝ ██╔══╝  ██╔══██╗
 ███████╗ ╚██████╗ ╚██████╔╝███████╗ ███╗     ██║      ██║    ██║     ███████╗██║  ██║
 ╚══════╝  ╚═════╝  ╚═════╝ ╚══════╝ ╚══      ╚═╝      ╚═╝    ╚═╝     ╚══════╝╚═╝  ╚═╝

                    🧬 Comprehensive E. coli Genotyping Tool 🧬
"""

SCIENCE_QUOTES = [
    "The important thing is to never stop questioning. - Albert Einstein",
    "Nothing in life is to be feared, it is only to be understood. - Marie Curie",
    "The greatest enemy of knowledge is not ignorance, it is the illusion of knowledge. - Stephen Hawking",
    "We are just an advanced breed of monkeys on a minor planet of a very average star. - Stephen Hawking",
    "The good thing about science is that it's true whether or not you believe in it. - Neil deGrasse Tyson",
    "Somewhere, something incredible is waiting to be known. - Carl Sagan",
    "DNA is like a computer program but far, far more advanced than any software ever created. - Bill Gates",
    "The most exciting phrase to hear in science is not 'Eureka!' but 'That's funny...' - Isaac Asimov"
]

FOOTER_MESSAGES = [
    "🔬 Precision typing for E. coli surveillance",
    "🦠 Transforming sequences into strain insights", 
    "⚡ Accelerating E. coli genomics research",
    "🌡️ Cultivating data for outbreak investigations",
    "🧪 Your partner in E. coli genotyping",
    "💡 Where bioinformatics meets microbiology"
]

def print_banner():
    """Print the ecoliTyper banner with a random science quote"""
    print(ECOLI_BANNER, file=sys.stderr)
    
    idx = int(datetime.now().timestamp() // 300) % len(SCIENCE_QUOTES)
    print("=" * 70, file=sys.stderr)
    print("Version 1.0.0 | Comprehensive E. coli Genotyping", file=sys.stderr)
    print("Author: Beckley Brown <brownbeckley94@gmail.com>", file=sys.stderr)
    print("", file=sys.stderr)
    print("💡", SCIENCE_QUOTES[idx], file=sys.stderr)
    print("", file=sys.stderr)

def print_footer(start_time):
    """Print completion footer with timing information"""
    end_time = datetime.now()
    duration = end_time - start_time
    
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    footer = f"""
┌──────────────────────────────────────────────────────────────────────┐
│                            🎉 ANALYSIS COMPLETE!                     │
├──────────────────────────────────────────────────────────────────────┤
│ ⏰  Time elapsed: {int(hours):02d}:{int(minutes):02d}:{seconds:04.1f}│
│ 📊  Results saved to output directory                                │
│                                                                      │
│ {random.choice(FOOTER_MESSAGES):^68}                                 │
│                                                                      │
│ 📚 If you use EcoliTyper in your research, please cite:              │
│    Brown, B. (2025). EcoliTyper: Unified MLST + Serotyping +         │
│    Clermont typing for Escherichia coli. GitHub repository:          │
│    https://github.com/bbeckley-hub/ecoliTyper                        │
│                                                                      │
│ 🧬 Enjoy your downstream analysis!                                   │
└──────────────────────────────────────────────────────────────────────┘
"""
    print(footer, file=sys.stderr)

def print_module_start(module_name):
    """Print module start message"""
    print(f"🧬 Running {module_name}...", file=sys.stderr)

def print_module_success(module_name, result=None):
    """Print module completion message"""
    if result:
        print(f"✅ {module_name}: {result}", file=sys.stderr)
    else:
        print(f"✅ {module_name} completed", file=sys.stderr)

def print_module_error(module_name, error):
    """Print module error message"""
    print(f"❌ {module_name} failed: {error}", file=sys.stderr)

# ===== Utilities =====
def log(msg: str):
    print(msg, file=sys.stderr, flush=True)

def run_cmd(cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, capture_output=True, text=True, check=False)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def get_bundled_tool_path(tool_name: str) -> Optional[Path]:
    """Dynamically get the path to bundled tools"""
    # Try multiple possible base directories
    possible_base_dirs = [
        Path(__file__).resolve().parent.parent.parent,  # ecoliTyper/ecoliTyper/ecolityper
        Path(__file__).resolve().parent.parent,         # ecoliTyper/ecolityper  
        Path(__file__).resolve().parent,                # ecolityper
        Path.cwd(),                                     # Current directory
    ]
    
    tool_paths = {
        'mlst': "database/mlst/bin/mlst",
        'serotypefinder': "database/serotypefinder/serotypefinder.py",
        'serotypefinder_db': "database/serotypefinder/serotypefinder_db",
    }
    
    for base_dir in possible_base_dirs:
        path = base_dir / tool_paths.get(tool_name, "")
        if path.exists():
            return path
    
    return None

# ===== Environment =====
def check_environment() -> Dict[str, Optional[str]]:
    """Check for required tools including ezclermont from pip"""
    tools = {
        "mlst": str(get_bundled_tool_path('mlst')) or shutil.which("mlst"),
        "serotypefinder": str(get_bundled_tool_path('serotypefinder')),
        "ezclermont": shutil.which("ezclermont"),  # From pip install
        "blastn": shutil.which("blastn"),
        "makeblastdb": shutil.which("makeblastdb"),
        "python": sys.executable
    }
    return tools

def print_environment_report(tools: Dict[str, Optional[str]]):
    """Print environment check with ASCII art style"""
    print("\n" + "🔧" * 20 + " TOOL CHECK " + "🔧" * 20, file=sys.stderr)
    
    status_icons = {True: "✅", False: "❌"}
    
    checks = [
        ("MLST", tools["mlst"]),
        ("SerotypeFinder", tools["serotypefinder"]),
        ("EzClermont", tools["ezclermont"]),
        ("BLASTN", tools["blastn"]),
        ("MakeBLASTDB", tools["makeblastdb"])
    ]
    
    for name, path in checks:
        status = status_icons[bool(path)]
        print(f"  {status} {name:15} : {path or 'NOT FOUND'}", file=sys.stderr)
    
    # Check databases
    serotype_db = get_bundled_tool_path('serotypefinder_db')
    db_status = status_icons[bool(serotype_db)]
    print(f"  {db_status} {'Serotype DB':15} : {'Found' if serotype_db else 'NOT FOUND'}", file=sys.stderr)
    
    print("🔧" * 52, file=sys.stderr)

# ===== MLST =====
def run_mlst(sample: Path, mlst_bin: Optional[str]) -> Tuple[str, str, str]:
    """Run MLST and return (scheme, ST, alleles)"""
    print_module_start("MLST")
    
    if not mlst_bin or mlst_bin == "None":
        error = f"MLST binary not found"
        print_module_error("MLST", error)
        return "NA", "NA", "NA"
    
    if not os.access(mlst_bin, os.X_OK):
        error = f"MLST binary not executable: {mlst_bin}"
        print_module_error("MLST", error)
        return "NA", "NA", "NA"
    
    if not sample.exists():
        error = f"Input file does not exist: {sample}"
        print_module_error("MLST", error)
        return "NA", "NA", "NA"
    
    # Set PERL5LIB environment variable for mlst
    env = os.environ.copy()
    mlst_path = Path(mlst_bin)
    perl5lib_path = mlst_path.parent.parent / "perl5"
    if perl5lib_path.exists():
        env['PERL5LIB'] = str(perl5lib_path)
    
    # Run mlst from the directory containing the binary
    mlst_dir = mlst_path.parent
    cp = run_cmd([mlst_bin, str(sample)], cwd=mlst_dir, env=env)
    
    if cp.returncode != 0:
        error = f"Command failed: {cp.stderr}"
        print_module_error("MLST", error)
        return "NA", "NA", "NA"
    
    # Parse MLST output
    lines = cp.stdout.strip().splitlines()
    
    for line in lines:
        if str(sample.name) in line or str(sample) in line:
            parts = line.split("\t")
            if len(parts) >= 3:
                scheme = parts[1]
                st = parts[2]
                alleles = parts[3] if len(parts) > 3 else ""
                print_module_success("MLST", f"ST{st} ({scheme})")
                return scheme, st, alleles
    
    error = f"No valid output found for {sample.name}"
    print_module_error("MLST", error)
    return "NA", "NA", "NA"

# ===== SerotypeFinder =====
def run_serotypefinder(sample: Path, serotypefinder_script: Optional[str], tmpdir: Path) -> Tuple[str, str, str, Optional[Path]]:
    """Run SerotypeFinder and return (O_type, H_type, full_serotype, json_path)"""
    print_module_start("Serotyping")
    
    if not serotypefinder_script or serotypefinder_script == "None":
        error = "SerotypeFinder script not found"
        print_module_error("Serotyping", error)
        return "NA", "NA", "NA", None
    
    serotype_db = get_bundled_tool_path('serotypefinder_db')
    if not serotype_db:
        error = "Database not found"
        print_module_error("Serotyping", error)
        return "NA", "NA", "NA", None
    
    # Create output directory for this sample
    sample_outdir = tmpdir / "serotypefinder_out"
    ensure_dir(sample_outdir)
    
    # Run SerotypeFinder - use the exact command that works
    cmd = [
        sys.executable, str(serotypefinder_script),
        "-i", str(sample),
        "-o", str(sample_outdir),
        "-p", str(serotype_db)
    ]
    
    cp = run_cmd(cmd)
    
    if cp.returncode != 0:
        error = f"Command failed: {cp.stderr}"
        print_module_error("Serotyping", error)
        return "NA", "NA", "NA", None
    
    # Look for JSON result file - SerotypeFinder creates data.json in output directory
    json_file = sample_outdir / "data.json"
    
    if not json_file.exists():
        # Check if there are subdirectories with JSON files
        subdirs = [d for d in sample_outdir.iterdir() if d.is_dir()]
        for subdir in subdirs:
            potential_json = subdir / "data.json"
            if potential_json.exists():
                json_file = potential_json
                break
    
    if not json_file.exists():
        print_module_error("Serotyping", "No results found")
        return "NA", "NA", "NA", None
    
    try:
        with open(json_file) as f:
            data = json.load(f)
        
        # Parse the actual SerotypeFinder JSON structure
        o_type = "NA"
        h_type = "NA"
        serotype = "NA"
        
        # The JSON has a 'serotypefinder' root key
        if "serotypefinder" in data:
            sf_data = data["serotypefinder"]
            
            # Look for results in the serotypefinder section
            if "results" in sf_data:
                results = sf_data["results"]
                
                # Extract H type
                if "H_type" in results and results["H_type"]:
                    h_data = list(results["H_type"].values())[0]  # Get first H type result
                    h_type = h_data.get("serotype", "NA")
                
                # Extract O type  
                if "O_type" in results and results["O_type"]:
                    o_data = list(results["O_type"].values())[0]  # Get first O type result
                    o_type = o_data.get("serotype", "NA")
                
                # Create full serotype
                if o_type != "NA" and h_type != "NA":
                    serotype = f"{o_type}:{h_type}"
                elif o_type != "NA":
                    serotype = o_type
                elif h_type != "NA":
                    serotype = h_type
        
        if o_type == "NA" and h_type == "NA":
            print_module_error("Serotyping", "No O or H type found")
            return "NA", "NA", "NA", json_file
        
        result_str = f"{o_type}:{h_type}" if serotype == "NA" else serotype
        print_module_success("Serotyping", result_str)
        return o_type, h_type, serotype, json_file
        
    except Exception as e:
        error = f"Error parsing JSON: {e}"
        print_module_error("Serotyping", error)
        return "NA", "NA", "NA", json_file

# ===== Clermont Typing =====
def run_clermont(sample: Path, ezclermont_bin: Optional[str]) -> Tuple[str, str]:
    """Run Clermont phylotyping and return (phylotype, method)"""
    print_module_start("Clermont typing")
    
    if not ezclermont_bin:
        error = "ezclermont not found (install with: pip install ezclermont)"
        print_module_error("Clermont", error)
        return "NA", "NA"
    
    # Run ezclermont on the sample
    cmd = [ezclermont_bin, str(sample)]
    cp = run_cmd(cmd)
    
    if cp.returncode != 0:
        error = f"Command failed: {cp.stderr}"
        print_module_error("Clermont", error)
        return "NA", "NA"
    
    if not cp.stdout.strip():
        error = "No output produced"
        print_module_error("Clermont", error)
        return "NA", "NA"
    
    # Parse ezclermont output
    output = cp.stdout.strip()
    
    phylotype = "NA"
    method = "PCR"
    
    # Parse the tab-separated output: "ecoli    B1"
    lines = output.split('\n')
    for line in lines:
        line = line.strip()
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 2:
                potential_phylo = parts[1].strip()
                if potential_phylo in ['A', 'B1', 'B2', 'C', 'D', 'E', 'F', 'G']:
                    phylotype = potential_phylo
                    break
    
    if phylotype != "NA":
        result_str = f"{phylotype} ({method})"
        print_module_success("Clermont", result_str)
        return phylotype, method
    
    print_module_error("Clermont", "Could not parse phylotype")
    return "NA", "NA"

# ===== Process Sample =====
def process_sample(sample: Path, tools: Dict[str, Optional[str]], outdir: Path) -> Dict[str, str]:
    log(f"📁 Processing: {sample.name}")
    
    ensure_dir(outdir)
    tmpdir = Path(tempfile.mkdtemp(prefix=f"ecolityper_{sample.stem}_"))
    
    # Run all typing methods
    mlst_scheme, mlst_st, mlst_alleles = run_mlst(sample, tools.get("mlst"))
    O_type, H_type, serotype, serotype_json_path = run_serotypefinder(sample, tools.get("serotypefinder"), tmpdir)
    clermont_phylotype, clermont_method = run_clermont(sample, tools.get("ezclermont"))
    
    # Copy serotype JSON to output directory if it exists
    serotype_json_output = None
    if serotype_json_path and serotype_json_path.exists():
        serotype_json_output = outdir / f"{sample.stem}_serotype.json"
        shutil.copy2(serotype_json_path, serotype_json_output)
    
    # Cleanup temporary directory
    try:
        shutil.rmtree(tmpdir)
    except Exception:
        pass
    
    # Prepare results
    detail = {
        "sample": sample.name,
        "mlst_scheme": mlst_scheme,
        "mlst_ST": mlst_st,
        "mlst_alleles": mlst_alleles,
        "O_type": O_type,
        "H_type": H_type,
        "serotype": serotype,
        "clermont_phylotype": clermont_phylotype,
        "clermont_method": clermont_method,
        "typing_date": datetime.now().isoformat(),
        "serotype_json_file": str(serotype_json_output) if serotype_json_output else "NA"
    }
    
    # Save individual sample results
    result_json = outdir / f"{sample.stem}.ecolityper.json"
    with result_json.open("w") as f:
        json.dump(detail, f, indent=2)
    
    return detail

# ===== Database Updates =====
def try_update_databases(tools: Dict[str, Optional[str]]):
    log("[Update] Database update feature coming soon!")

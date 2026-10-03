"""Golden set: the 10 trial companies with their expected grade (docs/BAGLAM.md section 9).
After every rule change run this; it lists every company whose type or grade changed.
Run: python3 altin_set.py   (exit code 1 if a grade differs)"""
import sys
from karne_deneme import analyse, load_yahoo

EXPECTED = {  # ticker: (grade, lynch_type)
    "KO": ("solid", "slow_grower"), "NVDA": ("solid", "cyclical"), "NKE": ("mid", "slow_grower"),
    "SBUX": ("mid", "slow_grower"), "PFE": ("weak", "slow_grower"), "INTC": ("weak", "cyclical"),
    "BA": ("weak", "cyclical"), "SNAP": ("weak", "unprofitable"), "DOW": ("weak", "cyclical"),
    "RIVN": ("weak", "unprofitable"),
}

yahoo = load_yahoo()
bad = 0
print(f"{'ticker':6} {'expected':22} {'now':22} ")
for t, (grade, typ) in EXPECTED.items():
    r = analyse(t, yahoo)
    now = (r["grade"], r["lynch_type"])
    ok = now[0] == grade
    bad += not ok
    note = "" if ok and now[1] == typ else ("  ← GRADE CHANGED" if not ok else "  ← type changed")
    print(f"{t:6} {grade + ' / ' + typ:22} {now[0] + ' / ' + now[1]:22}{note}")
print(f"\n{len(EXPECTED) - bad}/{len(EXPECTED)} grades as expected")
sys.exit(1 if bad else 0)

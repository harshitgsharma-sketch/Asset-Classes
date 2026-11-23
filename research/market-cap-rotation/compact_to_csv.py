"""Convert compact 'key=YYYYMM:value ...' lines (one per series) into data/<key>.csv files."""
import sys, os
src, out = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "data"
os.makedirs(out, exist_ok=True)
for line in open(src):
    line = line.strip()
    if "=" not in line: continue
    key, body = line.split("=", 1)
    cols = "P/E,P/B" if key.startswith("pe") else "Total Returns Index"
    with open(os.path.join(out, key + ".csv"), "w") as f:
        f.write("Date," + cols + "\n")
        for tok in body.split():
            ym, vals = tok.split(":", 1)
            f.write(f"{ym[:4]}-{ym[4:]}-28," + vals.replace("/", ",") + "\n")
    print(key, len(body.split()))

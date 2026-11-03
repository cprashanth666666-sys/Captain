import sys, nbformat as nbf
from nbclient import NotebookClient
src, dst = sys.argv[1], sys.argv[2]
nb = nbf.read(src, as_version=4)
c = NotebookClient(nb, timeout=1800, kernel_name="python3", allow_errors=True, resources={"metadata": {"path": "."}})
c.execute()
nbf.write(nb, dst)
bad = 0
for i, cell in enumerate(nb.cells):
    for o in cell.get("outputs", []):
        if o.output_type == "error":
            bad += 1; print("CELL", i, o.ename, o.evalue[:300]); print("\n".join(o.traceback[-3:])[:1200])
print("errors:", bad)

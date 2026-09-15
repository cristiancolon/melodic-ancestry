"""Seed the Ledger from Wikidata and MusicBrainz. Small live queries, no bulk dumps."""
import sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from hookline.ledger import Ledger

led = Ledger()
try:
    n = led.fetch_wikidata(limit=600)
    print(f"wikidata: {n} P144 edges on musical-work types")
except Exception as e:
    print("wikidata failed:", e)

# The chain this project started from. Fetched to see what the curated layer records.
SEEDS = {
    "Llorando se fue": "0e681ae3-8df5-4979-b1e3-0c3c2d4b14f9",
    "On the Floor": "0af83df7-71e6-4865-a44e-a6afd38d0da7",
    "Chorando se foi (Lambada)": "d8113087-c12d-4486-af0f-b8547f117ea3",
}
for name, mbid in SEEDS.items():
    for attempt in range(3):
        try:
            n = led.fetch_musicbrainz_work(mbid)
            print(f"musicbrainz {name}: {n} work-rel edges")
            break
        except Exception as e:
            print(f"  retry {name}: {e}")
            time.sleep(2.5)

print("\nstats:", led.stats())
lin = led.lineage("llorando")
if lin.get("found"):
    print(f"\nlineage for {lin['node']}:")
    for e in lin["antecedents"][:8]:
        print(f"   {e['from']}  --{e['relation']}-->  {e['to']}   [{e['source']}]")
    for e in lin["descendants"][:8]:
        print(f"   {e['to']}  <--{e['relation']}--  {e['from']}   [{e['source']}]")
print("\ntop Katz:")
for label, val in led.katz()[:8]:
    print(f"   {val:7.3f}  {label}")

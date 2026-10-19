"""Merge two Binderdex databases (e.g. a copy from your PC and the one on your server).

Usage:
  python merge_db.py SOURCE.db TARGET.db            preview only, nothing is written
  python merge_db.py SOURCE.db TARGET.db --apply    writes into TARGET.db (a backup copy is created first)

What happens:
- Cards from SOURCE that are missing in TARGET are added
- If a card exists in both, the higher quantity wins
- Binder entries from SOURCE are added if the Pokémon has no binder card in TARGET yet
- If both have a different binder card, TARGET keeps its card and the conflict is listed
- Favorites and wishlist entries are merged as well
Not merged: deleted cards (a card you deleted only in TARGET comes back from SOURCE).
Tip: stop the app before copying a database file, and merge into a copy."""
import datetime
import os
import shutil
import sqlite3
import sys


def cols(con, schema, table):
    return [r[1] for r in con.execute(f"PRAGMA {schema}.table_info({table})")]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) != 2 or not all(os.path.exists(a) for a in args):
        print(__doc__)
        sys.exit(1)
    src_path, dst_path = args
    if apply:
        backup = f"{dst_path}.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}"
        shutil.copy2(dst_path, backup)
        print("Backup of TARGET:", backup)

    dst = sqlite3.connect(dst_path)
    dst.execute("ATTACH DATABASE ? AS src", (src_path,))

    common = [c for c in cols(dst, "main", "cards") if c in cols(dst, "src", "cards")]
    cl = ", ".join(common)
    new = dst.execute("SELECT COUNT(*) FROM src.cards WHERE id NOT IN (SELECT id FROM main.cards)").fetchone()[0]
    qty = dst.execute("""SELECT m.name, m.qty, s.qty FROM main.cards m JOIN src.cards s ON s.id = m.id
                         WHERE s.qty > m.qty""").fetchall()
    dst.execute(f"INSERT OR IGNORE INTO main.cards({cl}) SELECT {cl} FROM src.cards")
    dst.execute("""UPDATE main.cards SET qty = (SELECT s.qty FROM src.cards s WHERE s.id = main.cards.id)
                   WHERE id IN (SELECT m.id FROM main.cards m JOIN src.cards s ON s.id = m.id WHERE s.qty > m.qty)""")
    pc = ", ".join(c for c in cols(dst, "main", "pokemon") if c in cols(dst, "src", "pokemon"))
    dst.execute(f"INSERT OR IGNORE INTO main.pokemon({pc}) SELECT {pc} FROM src.pokemon")

    def has(schema, table):
        return dst.execute(f"SELECT 1 FROM {schema}.sqlite_master WHERE name=?", (table,)).fetchone()

    wish_new = 0
    if has("main", "wishlist") and has("src", "wishlist"):
        wish_new = dst.execute("SELECT COUNT(*) FROM src.wishlist WHERE card_id NOT IN (SELECT card_id FROM main.wishlist) AND card_id NOT IN (SELECT id FROM main.cards)").fetchone()[0]
        wc = ", ".join(c for c in cols(dst, "main", "wishlist") if c in cols(dst, "src", "wishlist"))
        dst.execute(f"INSERT OR IGNORE INTO main.wishlist({wc}) SELECT {wc} FROM src.wishlist WHERE card_id NOT IN (SELECT id FROM main.cards)")
    fav_new = 0
    if has("main", "favorites") and has("src", "favorites"):
        fav_new = dst.execute("SELECT COUNT(*) FROM src.favorites WHERE dex_id NOT IN (SELECT dex_id FROM main.favorites)").fetchone()[0]
        dst.execute("INSERT OR IGNORE INTO main.favorites SELECT * FROM src.favorites")

    added, conflicts = 0, []
    for dex_id, card_id in dst.execute("SELECT dex_id, card_id FROM src.binder").fetchall():
        if not dst.execute("SELECT 1 FROM main.cards WHERE id=?", (card_id,)).fetchone():
            continue
        cur = dst.execute("SELECT card_id FROM main.binder WHERE dex_id=?", (dex_id,)).fetchone()
        if cur is None:
            dst.execute("INSERT INTO main.binder VALUES(?,?)", (dex_id, card_id))
            added += 1
        elif cur[0] != card_id:
            def label(cid):
                r = dst.execute("SELECT name, set_name, local_id FROM main.cards WHERE id=?", (cid,)).fetchone()
                return f"{r[0]} ({r[1]} {r[2]})" if r else cid
            p = dst.execute("SELECT name FROM main.pokemon WHERE id=?", (dex_id,)).fetchone()
            conflicts.append((p[0] if p else f"#{dex_id}", label(cur[0]), label(card_id)))

    print(f"New cards:                    {new}")
    print(f"Higher quantity taken over:   {len(qty)}")
    for n, a, b in qty:
        print(f"   {n}: {a} -> {b}")
    print(f"New binder entries:           {added}")
    print(f"New favorites:                {fav_new}")
    print(f"New wishlist cards:           {wish_new}")
    print(f"Binder conflicts (TARGET stays): {len(conflicts)}")
    for p, a, b in conflicts:
        print(f"   {p}: TARGET has {a}, SOURCE has {b}")

    if apply:
        dst.commit()
        print("Done, TARGET was updated.")
    else:
        dst.rollback()
        print("\nPreview only, nothing was written. Add --apply to write the changes.")
    dst.close()


if __name__ == "__main__":
    main()

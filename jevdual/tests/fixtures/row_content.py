"""Synthetic columns/text with retained NS-1001 descendant roles, no live AX reads.
Derived from Opus632ba72 probe. Header/column mapping and text values are NOT
established by the retained ancestry evidence; this fixture supplies them.
"""

def mk():
    nodes = []
    def add(id, role, parent, **f):
        n = {"id": id, "pid": 77, "window_id": 40335, "role": role, "name": "", "value": None, "url": None,
             "parent": parent, "children": [], "rows": None, "columns": None, "header": None,
             "enabled": None, "actions": [], "error": None}
        n.update(f); nodes.append(n)
        if parent is not None:
            next(p for p in nodes if p["id"] == parent)["children"].append(id)
        return n
    return nodes, add

def live_shape(checkbox=True, two_texts=True, popup_image=True, link=False, header_select=False):
    """Mirror the retained live NS-1001 row (row-diagnosis RETAINED-ROW-ANCESTRY.json):
    AXRow -> [AXCell>AXCheckBox 'Select row', AXCell>AXGroup>AXStaticText, AXCell>2xAXStaticText,
    4x AXCell>AXStaticText, AXCell>AXPopUpButton 'Open menu'>(AXImage, AXStaticText)].
    Columns/AXHeader are NOT in the retained evidence; they are supplied favourably here."""
    nodes, add = mk()
    add(0, "AXWindow", None); add(1, "AXWebArea", 0, url="http://127.0.0.1:5176/tasks")
    headers = ["", "ID", "Title", "Status", "Priority", "Assignee", "Due", ""]
    table = add(2, "AXTable", 1, rows=[3], columns=[])
    add(3, "AXRow", 2)
    for c, h in enumerate(headers):
        add(4 + c, "AXCell", 3, name=h)
    colcells = {c: [4 + c] for c in range(len(headers))}
    nid = [2000]
    def nxt():
        nid[0] += 1; return nid[0]
    for r, key in enumerate(["NS-1001", "NS-1002"]):
        rid = 100 + r * 50
        table["rows"].append(rid); add(rid, "AXRow", 2)
        vals = {1: key, 3: "Open", 4: "High", 5: "Ada", 6: "Nov 20"}
        for c in range(len(headers)):
            cid = rid + 1 + c
            add(cid, "AXCell", rid); colcells[c].append(cid)
            if c == 0:
                if checkbox: add(nxt(), "AXCheckBox", cid, name="Select row")
            elif c == 1:
                g = add(nxt(), "AXGroup", cid); add(nxt(), "AXStaticText", g["id"], value=key)
            elif c == 2:
                if link:
                    l = add(nxt(), "AXLink", cid, name=f"Task {r}"); add(nxt(), "AXStaticText", l["id"], value=f"Task {r}")
                else:
                    add(nxt(), "AXStaticText", cid, value=f"Task title {r}")
                    if two_texts: add(nxt(), "AXStaticText", cid, value=f"subtitle {r}")
            elif c == len(headers) - 1:
                pb = add(940 + r, "AXPopUpButton", cid, name="Open menu", enabled=True, actions=["AXPress", "AXShowMenu"])
                if popup_image:
                    add(nxt(), "AXImage", pb["id"]); add(nxt(), "AXStaticText", pb["id"], value="Open menu")
            else:
                add(nxt(), "AXStaticText", cid, value=vals[c])
    for c in range(len(headers)):
        add(30 + c, "AXColumn", 2, children=colcells[c], header=4 + c); table["columns"].append(30 + c)
    if header_select:
        add(nxt(), "AXCheckBox", 4, name="Select all")
    return {"root": 0, "complete": True, "nodes": nodes}

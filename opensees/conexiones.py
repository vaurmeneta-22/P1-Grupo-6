# -*- coding: utf-8 -*-
"""
CONEXIONES - planificador de conectividad del modelo
=====================================================
Reglas (aprobadas por el usuario):
  A) extremo de muro que COINCIDE (<2.5cm en planta, mismo nivel) con un nodo
     de marco -> reutilizar el nodo del contrato (NO se crea tag 9000).
  B) extremo de muro a <20cm del INTERIOR de una viga (pie perpendicular dentro
     del tramo) -> crear nodo en la viga en el pie, subdividir la viga en
     fracciones elasticBeamColumn y unir muro <-> nodo con rigidLink 'beam'.
  C) extremo de muro a <20cm de un nodo i/j de viga (mismo nivel) -> rigidLink
     'beam' directo muro <-> nodo i/j.
  D) muro paralelo adosado a viga -> cubierto por B (pie perpendicular).
  E) extremo de muro a <25cm de un nodo de columna (mismo nivel) -> rigidLink
     'beam' directo muro <-> columna.
Apoyos huerfanos (38): nodos del contrato en supports sin elemento propio. Se
  crean y, si hay un nodo estructural a <30cm en el MISMO plano (|dz|<=10cm),
  se unen como esclavos con rigidLink 'bar'; si no, quedan fijos de tierra.

Tags reservados (contrato compartido generador <-> exportador):
  - nodos del contrato estructurales : id del contrato (1..536)
  - nodos de muro                   : 9000+
  - nodos de conexion (pie en viga) : 200000+
  - fracciones de viga subdividida  : 300000+  (la 1a fraccion conserva el tag
                                       del contrato para el viewer 1:1)

Modulo PURO (no importa OpenSees): lo usan opensees_edificio_v2.py y
exportar_analysis_map.py para que los tags coincidan exactamente.
"""
import os
import math
import json

CM_TO_M = 0.01

TOL_NODO = 0.025      # regla A  (m)
TOL_VIGA = 0.20       # reglas B/C/D (m)
TOL_COL = 0.25        # regla E (m)
TOL_APOYO = 0.30      # apoyos huerfanos (m) - mismo plano

WALL_TAG_START = 9000
SPLIT_NODE_START = 200000
SPLIT_ELEM_START = 300000

REGLA_G_FILE = "regla_g_walls.json"   # seleccion del usuario (muro_seleccion.html)


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_regla_g_walls():
    """Lee la seleccion {walls:[...]} de regla_g_walls.json en la raiz.
    Si falta el archivo -> lista vacia (Regla G inactiva, comportamiento previo)."""
    path = os.path.join(_repo_root(), REGLA_G_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        walls = data.get("walls", []) if isinstance(data, dict) else data
        return [int(w) for w in walls]
    except (OSError, ValueError, TypeError):
        return []


def _wall_section_dims(e):
    """(b_cm, W_cm) del muro: espesor b y ancho de panel W en planta.
    Prioriza la seccion 'BxW' (p.ej. 25x795); el campo 'h' del JSON es
    inconsistente en algunos tramos (31x x=57.5: 315-318 tienen h=795 y
    319 h=356 pese a seccion 25x795), por eso se usa el string de seccion."""
    try:
        b_raw, w_raw = str(e.get("section", "")).lower().split("x")
        return float(b_raw), float(w_raw)
    except (ValueError, AttributeError):
        return float(e.get("b", 0.0)), float(e.get("h", 0.0))


def _build_plan(nodes_json, elements_json, supports):
    """Devuelve el plan de conectividad completo (dict)."""
    structural_refs = set()
    for e in elements_json:
        if e["type"] == "loza":
            continue
        if "node_i" in e:
            structural_refs.add(e["node_i"])
            structural_refs.add(e["node_j"])

    supports_by_id = {s["node"] for s in supports}
    isolated_ids = {s_id for s_id in supports_by_id if s_id not in structural_refs}

    # --- 1. Nodos estructurales del contrato ------------------------------
    node_tags = {}        # id JSON -> tag OpenSees (identidad para contrato)
    pos_key = {}          # (x, y, z) redondeado -> tag
    tag_coord = {}        # tag -> (x, y, z)
    for n in nodes_json:
        nid = n["id"]
        if nid in structural_refs or (nid in supports_by_id and nid not in isolated_ids):
            x = n["x"] * CM_TO_M
            y = n["y"] * CM_TO_M
            z = n["z"] * CM_TO_M
            key = (round(x, 4), round(y, 4), round(z, 4))
            node_tags[nid] = nid
            pos_key[key] = nid
            tag_coord[nid] = (x, y, z)

    # --- 2. Nodos de muro (9000+) con reuso por regla A --------------------
    wall_elems = [e for e in elements_json if e["type"] == "wall"]
    next_wall = [WALL_TAG_START]
    wall_ends = {}        # wall id -> (tagA, tagB)
    wall_node_coords = []  # (tag, x, y, z) de nodos NUEVOS (para ops.node)

    def wall_node_from_cm(ccx, ccz, ccy):
        """cx_cm, cz_cm = plan del JSON wall; ccy_cm = altura."""
        x, y, z = ccx * CM_TO_M, ccz * CM_TO_M, ccy * CM_TO_M
        key = (round(x, 4), round(y, 4), round(z, 4))
        if key in pos_key:
            return pos_key[key]                     # reuso exacto (v2 legacy)
        for (kx, ky, kz), ktag in pos_key.items():  # regla A (tolerancia)
            if abs(kz - z) < 1e-4 and math.hypot(kx - x, ky - y) < TOL_NODO:
                return ktag
        tag = next_wall[0]
        next_wall[0] += 1
        pos_key[key] = tag
        tag_coord[tag] = (x, y, z)
        wall_node_coords.append((tag, x, y, z))
        return tag

    for e in wall_elems:
        tagA = wall_node_from_cm(e["xi"], e["zi"], e["yi"])
        tagB = wall_node_from_cm(e["xj"], e["zj"], e["yj"])
        wall_ends[e["id"]] = (tagA, tagB)

    # --- 3. Rejilla de vigas/columnas por nivel ---------------------------
    beams = [e for e in elements_json if e["type"] in ("beam_x", "beam_y")]
    columns = [e for e in elements_json if e["type"] == "column"]

    beam_elem = {}        # tag -> (ni, nj, coord_i, coord_j)
    for e in beams:
        i, j = e["node_i"], e["node_j"]
        if i not in tag_coord or j not in tag_coord:
            continue
        beam_elem[e["id"]] = (i, j, tag_coord[i], tag_coord[j])

    col_nodes = []        # (tag, x, y, z) extremos de columnas
    for e in columns:
        for nid in (e["node_i"], e["node_j"]):
            if nid in tag_coord:
                col_nodes.append((nid, *tag_coord[nid]))

    def dist_point_seg(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 < 1e-14:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
        qx, qy = x1 + t * dx, y1 + t * dy
        return math.hypot(px - qx, py - qy), t, qx, qy

    # --- 4. Reglas B/C/D/E por nodo de muro --------------------------------
    rigid_links = []      # (kind, master, slave)
    beam_split_pts = {}   # viga tag -> {key_pt: {"t", "wall_tags", "node"}}
    seen_link = set()

    wall_tags = set()
    for w in wall_elems:
        wall_tags.update(wall_ends[w["id"]])

    col_tag_set = {ctag for (ctag, _cx, _cy, _cz) in col_nodes}

    for tagW in sorted(wall_tags):
        x, y, z = tag_coord[tagW]
        best = None        # (dist, tipo, payload)
        # C y B: vigas del mismo nivel
        for e in beams:
            if e["id"] not in beam_elem:
                continue
            i, j, c1, c2 = beam_elem[e["id"]]
            if abs(c1[2] - z) > 1e-6:
                continue
            for ftag, fc in ((i, c1), (j, c2)):
                d = math.hypot(x - fc[0], y - fc[1])
                if d < TOL_VIGA and (best is None or d < best[0]):
                    best = (d, "C", ftag)
            d, t, qx, qy = dist_point_seg(x, y, c1[0], c1[1], c2[0], c2[1])
            if d < TOL_VIGA and 0.005 < t < 0.995:
                if best is None or d < best[0]:
                    best = (d, "B", (e["id"], round(qx, 6), round(qy, 6), t))
        # E: columnas del mismo nivel
        for (ctag, cx, cy, cz) in col_nodes:
            if abs(cz - z) > 1e-6:
                continue
            d = math.hypot(x - cx, y - cy)
            if d < TOL_COL and (best is None or d < best[0]):
                best = (d, "E", ctag)
        if best is None:
            continue
        d, tipo, pay = best
        if tipo == "C" or tipo == "E":
            if (tagW, pay) not in seen_link:
                rigid_links.append(("beam", pay, tagW))
                seen_link.add((tagW, pay))
        else:  # B
            vid, qx, qy, t = pay
            key_pt = (round(qx, 4), round(qy, 4))
            bucket = beam_split_pts.setdefault(vid, {})
            if key_pt not in bucket:
                bucket[key_pt] = {"t": t, "wall_tags": set(), "node": None}
            bucket[key_pt]["wall_tags"].add(tagW)

    # --- 4b. REGLA F: empalme viga-viga --------------------------------
    # Todo nodo estructural del contrato (que no sea columna) que yazga al
    # INTERIOR de otra viga (misma cota z, 0.005 < t < 0.995, tol 2.5 cm)
    # se reutiliza como punto de division de esa viga. Asi la secundaria que
    # aterriza comparte nodo (6 DOF) con la primaria continua.
    # Si el punto ya tenia un split de muro (regla B), se PRIORIZA el reuse.
    n_empalmes = 0
    for ntag, (nx, ny, nz) in sorted(tag_coord.items()):
        if ntag not in node_tags or ntag in col_tag_set:
            continue
        for vid, (i, j, c1, c2) in beam_elem.items():
            if ntag == i or ntag == j:
                continue
            if abs(c1[2] - nz) > 1e-6:
                continue
            d, t, qx, qy = dist_point_seg(nx, ny, c1[0], c1[1], c2[0], c2[1])
            if d < TOL_NODO and 0.005 < t < 0.995:
                key_pt = (round(nx, 4), round(ny, 4))
                bucket = beam_split_pts.setdefault(vid, {})
                if key_pt not in bucket:
                    bucket[key_pt] = {"t": t, "wall_tags": set(), "node": None}
                bucket[key_pt]["node"] = ntag
                n_empalmes += 1

    # --- 4c. REGLA G: voladizos apoyados en muros de fachada -------------
    # Seleccion del usuario (muro_seleccion.html) guardada en regla_g_walls.json:
    # muros 315..319 (fachada x=57.5, panel 25x795 en planta yz). Todo nodo
    # estructural del contrato que yazga DENTRO del panel del muro (espesor b en
    # x, ancho W en planta) y al MISMO nivel de un extremo del muro se une con
    # rigidLink 'beam' (MASTER = nodo de muro, SLAVE = nodo del contrato).
    # Asi las vigas 335..344 en voladizo se apoyan en la muralla real en vez de
    # quedar clavadas con suelo vertical artificial (casos_especiales).
    regla_g_nodes = set()      # nodos del contrato conectados (se liberan)
    g_tol = 0.02               # m, holgura de fabrica
    for gwid in _load_regla_g_walls():
        if gwid not in wall_ends:
            continue
        e = next((w for w in wall_elems if w["id"] == gwid), None)
        if e is None:
            continue
        b_cm, W_cm = _wall_section_dims(e)
        tagA, tagB = wall_ends[gwid]
        xa, ya, _za = tag_coord[tagA]
        xb, yb, _zb = tag_coord[tagB]
        # el panel mide b en x (espesor) y W en la planta (y del modelo);
        # ambos extremos del tramo vertical comparten centro en planta.
        for wtag, (xw, yw, zw) in ((tagA, tag_coord[tagA]),
                                   (tagB, tag_coord[tagB])):
            for ntag, (nx, ny, nz) in tag_coord.items():
                if ntag not in node_tags:
                    continue
                if abs(nz - zw) > 1e-6:
                    continue
                if abs(nx - xw) > b_cm * CM_TO_M / 2 + g_tol:
                    continue
                if abs(ny - yw) > W_cm * CM_TO_M / 2 + g_tol:
                    continue
                if (wtag, ntag) in seen_link:
                    continue
                # se conecta al nivel del tramo de muro correspondiente
                # (usa el centro xw,yw del panel; el nodo cae dentro del area)
                # kind 'eq3' => igualdad de traslaciones (ux,uy,uz) SIN el brazo
                # de 3.625m que rigidLink 'beam' amplificaria con el giro del
                # muro (rx ~1e-3 -> ~3.7mm de descuelgue artificial en la viga).
                rigid_links.append(("eq3", wtag, ntag))
                seen_link.add((wtag, ntag))
                regla_g_nodes.add(ntag)

    # --- 5. Materializar splits --------------------------------------------
    node_pool = [SPLIT_NODE_START]
    elem_pool = [SPLIT_ELEM_START]
    extra_nodes = []      # (tag, x, y, z)
    frame_split = {}      # viga tag -> [(frac_tag, ni, nj), ...] en orden
    for vid, pts in beam_split_pts.items():
        i, j, c1, c2 = beam_elem[vid]
        entries = sorted(pts.items(), key=lambda kv: kv[1]["t"])
        z = c1[2]
        for (key_pt, info) in entries:
            tagN = info["node"]
            if tagN is None:
                tagN = node_pool[0]
                node_pool[0] += 1
                qx, qy = key_pt
                extra_nodes.append((tagN, qx, qy, z))
                pos_key[key_pt + (round(z, 4),)] = tagN
                tag_coord[tagN] = (qx, qy, z)
            info["node"] = tagN
            for wt in info["wall_tags"]:
                if (wt, tagN) not in seen_link:
                    rigid_links.append(("beam", tagN, wt))
                    seen_link.add((wt, tagN))
        segs = [(i, c1)] + [(info["node"], (0.0, 0.0, 0.0))
                            for _k, (key_pt, info) in enumerate(entries)] + [(j, c2)]
        fracc = []
        for k in range(len(segs) - 1):
            ni, _ = segs[k]
            nj, _ = segs[k + 1]
            if k == 0:
                ftag = vid                      # 1a fraccion conserva tag contrato
            else:
                ftag = elem_pool[0]
                elem_pool[0] += 1
            fracc.append((ftag, ni, nj))
        frame_split[vid] = fracc

    # --- 6. Apoyos huerfanos ----------------------------------------------
    orphan_nodes = []     # (tag, x, y, z, kind, master)
    for n in nodes_json:
        nid = n["id"]
        if nid not in isolated_ids:
            continue
        x, y, z = n["x"] * CM_TO_M, n["y"] * CM_TO_M, n["z"] * CM_TO_M
        best = None
        bd = TOL_APOYO
        for (kx, ky, kz), ktag in pos_key.items():
            if abs(kz - z) > 0.10:
                continue
            d = math.hypot(x - kx, y - ky)
            if d < bd:
                bd = d
                best = ktag
        if best is not None:
            orphan_nodes.append((nid, x, y, z, "bar", best))
        else:
            orphan_nodes.append((nid, x, y, z, "fix", None))
        node_tags[nid] = nid
        key = (round(x, 4), round(y, 4), round(z, 4))
        if key not in pos_key:
            pos_key[key] = nid
            tag_coord[nid] = (x, y, z)

    # --- 7. Apoyos finales (contrato + base de muros + huerfanos) ----------
    support_tags_final = set(s["node"] for s in supports)
    for (ax, ay, az), tag in pos_key.items():
        if az < 0.06 and tag not in support_tags_final:
            support_tags_final.add(tag)

    base_extra = sorted(tag for (ax, ay, az), tag in pos_key.items()
                        if az < 0.06 and tag not in set(s["node"] for s in supports))

    return {
        "pos_key": pos_key,
        "tag_coord": tag_coord,
        "node_tags": node_tags,
        "wall_ends": wall_ends,
        "wall_node_coords": wall_node_coords,
        "extra_nodes": extra_nodes,
        "frame_split": frame_split,
        "rigid_links": rigid_links,
        "regla_g_nodes": sorted(regla_g_nodes),
        "orphan_nodes": orphan_nodes,
        "support_tags": support_tags_final,
        "base_extra": base_extra,
        "n_empalmes": n_empalmes,
    }


def plan_conexiones(nodes_json, elements_json, supports):
    return _build_plan(nodes_json, elements_json, supports)


def load_plan(repo=None):
    repo = repo or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo, "Edificio.json"), encoding="utf-8") as f:
        data = json.load(f)
    return plan_conexiones(data["nodes"], data["elements"], data["supports"]), data


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p, data = load_plan()
    print("extra_nodes :", len(p["extra_nodes"]))
    print("rigid_links :", len(p["rigid_links"]))
    for k, m, s in p["rigid_links"]:
        print("   ", k, m, "->", s)
    print("frame_split :", len(p["frame_split"]))
    print("empalmes F  :", p["n_empalmes"])
    print("regla_g[G]  :", p["regla_g_nodes"])
    for vid, fr in sorted(p["frame_split"].items()):
        print("   ", vid, "->", [(ft, ni, nj) for ft, ni, nj in fr])
    print("orphan_nodes:", len(p["orphan_nodes"]))
    for o in p["orphan_nodes"]:
        print("   ", o)
    print("support_tags:", len(p["support_tags"]))
    print("base_extra  :", len(p["base_extra"]))
    print("wall_nodes  :", len(p["wall_node_coords"]))

    # --- verificacion de coherencia del plan -------------------------------
    ok = True
    # todos los extremos de viga/nodo de split existen en pos_key
    for vid, fr in p["frame_split"].items():
        for (_ft, ni, nj) in fr:
            if ni not in p["tag_coord"] or nj not in p["tag_coord"]:
                print(f"  [BUG] viga {vid}: nodo {ni}/{nj} sin coord")
                ok = False
    # todos los rigid links apuntan a nodos creados
    for (kind, m, s) in p["rigid_links"]:
        if m not in p["tag_coord"] or s not in p["tag_coord"]:
            print(f"  [BUG] rigid {kind} {m}->{s}: nodo sin coord")
            ok = False
    # toda falla tipográfica de fraccion con tag no duplicado
    tags_frac = [ft for fr in p["frame_split"].values() for (ft, _a, _b) in fr]
    dups = [x for x in set(tags_frac) if tags_frac.count(x) > 1]
    if dups:
        print("  [BUG] tags de fraccion duplicados:", dups)
        ok = False
    # nodos de conexion no chocan con tags de contrato
    nodos_extra = {t for (t, *_r) in p["extra_nodes"]}
    if nodos_extra & set(p["node_tags"]):
        print("  [BUG] nodos extra chocan con contrato")
        ok = False
    # cada viga fraccionada conserva su tag en la 1a fraccion
    for vid, fr in p["frame_split"].items():
        if fr[0][0] != vid:
            print(f"  [BUG] viga {vid}: 1a fraccion no conserva tag")
            ok = False
    print("PLAN OK" if ok else "PLAN CON BUGS")
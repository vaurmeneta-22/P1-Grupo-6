import json
import os
import re

def main():
    json_path = os.path.join(os.path.dirname(__file__), "..", "Edificio.json")
    with open(json_path, "r") as f:
        data = json.load(f)

    nodes = data["nodes"]
    elements = data["elements"]
    sections_list = data["sections"]
    sections = {s["name"]: s for s in sections_list}

    # Convert cm to m for display
    scale = 0.01

    # Build node lookup
    node_coords = {}
    for n in nodes:
        node_coords[n["id"]] = (n["x"] * scale, n["z"] * scale, n["y"] * scale)

    # Build elements for Three.js
    beam_h = (sections.get("60x80", {}).get("h", 80.0)) * scale
    col_top_extra = beam_h / 2

    elements_js = []
    for e in elements:
        if e.get("type") == "loza":
            continue  # losas NO se modelan como elementos estructurales
        if "node_i" in e:
            ni = node_coords[e["node_i"]]
            nj = node_coords[e["node_j"]]
        else:
            # muros con geometria directa (xi..zj en cm)
            ni = (e["xi"] * scale, e["yi"] * scale, e["zi"] * scale)
            nj = (e["xj"] * scale, e["yj"] * scale, e["zj"] * scale)
        sec = sections.get(e["section"])
        if sec is None:
            # fallback: seccion derivada de las dimensiones del contrato (cm)
            sec = {"b": e.get("b", 60.0), "h": e.get("h", 60.0)}
        b = sec["b"] * scale
        h = sec["h"] * scale
        etype = e["type"]

        xi, yi, zi = ni
        xj, yj, zj = nj

        if etype == "column":
            yj += col_top_extra
            yi -= e.get("ext_bot_cm", 0) * scale

        lift = e.get("lift_cm", 0) * scale
        yi += lift
        yj += lift

        if etype == "beam_y":
            zi += e.get("ext_start_cm", 0) * scale
            zj += e.get("ext_end_cm", 0) * scale
        elif etype == "beam_x":
            xi += e.get("ext_start_cm", 0) * scale
            xj += e.get("ext_end_cm", 0) * scale

        elements_js.append({
            "type": etype,
            "section": e["section"],
            "xi": xi, "yi": yi, "zi": zi,
            "xj": xj, "yj": yj, "zj": zj,
            "b": b, "h": h
        })

    # Build nodes for Three.js
    nodes_js = []
    for n in nodes:
        nodes_js.append({
            "id": n["id"],
            "x": n["x"] * scale,
            "y": n["z"] * scale,
            "z": n["y"] * scale
        })

    elements_json = json.dumps(elements_js)
    nodes_json = json.dumps(nodes_js)

    # Node ids that are supports (from the json "supports" array)
    supports_ids = set()
    for s in data.get("supports", []):
        supports_ids.add(s["node"])
    supports_json = json.dumps(sorted(supports_ids))

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Edificio 3D</title>
<style>
  body {{ margin: 0; overflow: hidden; background: #1a1a2e; font-family: monospace; }}
  #info {{
    position: absolute; top: 10px; left: 10px;
    color: #0f0; background: rgba(0,0,0,0.7);
    padding: 10px 15px; border-radius: 5px; font-size: 13px;
    z-index: 10;
  }}
  #legend {{
    position: absolute; bottom: 10px; left: 10px;
    color: #fff; background: rgba(0,0,0,0.7);
    padding: 10px 15px; border-radius: 5px; font-size: 12px;
    z-index: 10;
  }}
  #legend div {{ margin: 3px 0; }}
  #legend span {{ display: inline-block; width: 14px; height: 14px; margin-right: 8px; vertical-align: middle; border-radius: 2px; }}
</style>
</head>
<body>
<div id="info">
  Edificio 3D - Grupo 6<br>
  Click izq: Rotar | Click der: Mover | Scroll: Zoom | N: Nodos | E: Ejes<br>
  <b>Floor</b>: Subterraneo | Nodos: {len(nodes)} | Elementos: {len(elements)}
</div>
<div id="legend">
  <div><span style="background:#e74c3c;"></span>Columna 70x70</div>
  <div><span style="background:#3498db;"></span>Viga X 60x80</div>
  <div><span style="background:#2ecc71;"></span>Viga Y 60x80</div>
  <div><span style="background:#f1c40f;"></span>Nodo</div>
  <div><span style="background:#9b59b6;"></span>Apoyo empotrado</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
  const elements = {elements_json};
  const nodesData = {nodes_json};
  const supportsSet = new Set({supports_json});

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1a2e);
  scene.gridHelper = null;

  const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.01, 1000);
  const ORBIT_TARGET = new THREE.Vector3(-25, 9, 8);
  camera.position.set(-25, 30, 50);
  camera.lookAt(ORBIT_TARGET);

  const renderer = new THREE.WebGLRenderer({{antialias: true}});
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.shadowMap.enabled = true;
  document.body.appendChild(renderer.domElement);

  // Lights
  const ambLight = new THREE.AmbientLight(0x404060, 0.6);
  scene.add(ambLight);
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(10, 20, 10);
  dirLight.castShadow = true;
  scene.add(dirLight);
  const hemiLight = new THREE.HemisphereLight(0x8888aa, 0x444422, 0.4);
  scene.add(hemiLight);

  // Grid
  const gridHelper = new THREE.GridHelper(30, 30, 0x444466, 0x333355);
  gridHelper.position.y = 0;
  scene.add(gridHelper);

  // Axes
  const axesHelper = new THREE.AxesHelper(3);
  axesHelper.position.set(0, 0, 0);
  scene.add(axesHelper);

  // Axis labels
  function makeLabel(text, x, y, z, color) {{
    const canvas = document.createElement('canvas');
    canvas.width = 128; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.font = 'bold 40px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(text, 64, 45);
    const tex = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({{map: tex}});
    const sprite = new THREE.Sprite(mat);
    sprite.position.set(x, y, z);
    sprite.scale.set(1.5, 0.75, 1);
    scene.add(sprite);
  }}
  makeLabel('X', 12, 0, 0, '#e74c3c');
  makeLabel('Y', 0, 0, 18, '#3498db');
  makeLabel('Z', 0, 6, 0, '#2ecc71');

  // Colors
  const colors = {{
    column: 0xe74c3c,
    beam_x: 0x3498db,
    beam_y: 0x2ecc71
  }};

  // Draw elements
  const elementsGroup = new THREE.Group();
  elements.forEach(e => {{
    const start = new THREE.Vector3(e.xi, e.yi, e.zi);
    const end = new THREE.Vector3(e.xj, e.yj, e.zj);
    const dir = new THREE.Vector3().subVectors(end, start);
    const length = dir.length();
    const center = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);

    const color = colors[e.type] || 0xffffff;

    if (e.type === 'column') {{
      const w = e.b;
      const d = e.b;
      const h = length;
      const geom = new THREE.BoxGeometry(d, h, w);
      const mat = new THREE.MeshPhongMaterial({{color: color, transparent: true, opacity: 0.85}});
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.copy(center);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      elementsGroup.add(mesh);
    }} else {{
      const w = e.b;
      const h = e.h;
      let geom;
      if (e.type === 'beam_x') {{
        geom = new THREE.BoxGeometry(length, h, w);
      }} else {{
        geom = new THREE.BoxGeometry(w, h, length);
      }}
      const mat = new THREE.MeshPhongMaterial({{color: color, transparent: true, opacity: 0.85}});
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.copy(center);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      elementsGroup.add(mesh);
    }}

    // Wireframe
    let wireGeom;
    if (e.type === 'column') {{
      wireGeom = new THREE.EdgesGeometry(new THREE.BoxGeometry(e.b, length, e.b));
    }} else if (e.type === 'beam_x') {{
      wireGeom = new THREE.EdgesGeometry(new THREE.BoxGeometry(length, e.h, e.b));
    }} else {{
      wireGeom = new THREE.EdgesGeometry(new THREE.BoxGeometry(e.b, e.h, length));
    }}
    const wireMat = new THREE.LineBasicMaterial({{color: 0xffffff, transparent: true, opacity: 0.3}});
    const wire = new THREE.LineSegments(wireGeom, wireMat);
    wire.position.copy(center);
    elementsGroup.add(wire);
  }});
  scene.add(elementsGroup);

  // Stick axes (palitos): una linea por elemento entre sus extremos
  const axesGroup = new THREE.Group();
  elements.forEach(e => {{
    const stickMat = new THREE.LineBasicMaterial({{
      color: colors[e.type] || 0xffffff,
      linewidth: 2
    }});
    const pts = [
      new THREE.Vector3(e.xi, e.yi, e.zi),
      new THREE.Vector3(e.xj, e.yj, e.zj)
    ];
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    const line = new THREE.Line(g, stickMat);
    axesGroup.add(line);
  }});
  axesGroup.visible = false;
  scene.add(axesGroup);

  // Draw nodes
  const nodeGroup = new THREE.Group();
  const sphereGeom = new THREE.SphereGeometry(0.15, 16, 16);
  const nodeMat = new THREE.MeshPhongMaterial({{color: 0xf1c40f, emissive: 0x665500}});
  const supportMat = new THREE.MeshPhongMaterial({{color: 0x9b59b6, emissive: 0x442266}});

  nodesData.forEach(n => {{
    const isSupport = supportsSet.has(n.id);
    const mesh = new THREE.Mesh(sphereGeom, isSupport ? supportMat : nodeMat);
    mesh.position.set(n.x, n.y, n.z);
    mesh.castShadow = true;
    nodeGroup.add(mesh);

    // Node label
    const canvas = document.createElement('canvas');
    canvas.width = 64; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgba(0,0,0,0.75)';
    ctx.beginPath();
    ctx.arc(32, 32, 30, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 42px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(n.id), 32, 34);
    const tex = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({{map: tex, depthTest: false}});
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(n.x, n.y + 0.6, n.z);
    sprite.scale.set(0.9, 0.9, 1);
    sprite.renderOrder = 1000;
    nodeGroup.add(sprite);
  }});
  scene.add(nodeGroup);

  // Support symbols (triangles)
  nodesData.filter(n => supportsSet.has(n.id)).forEach(n => {{
    const shape = new THREE.Shape();
    shape.moveTo(-0.4, 0);
    shape.lineTo(0.4, 0);
    shape.lineTo(0, -0.6);
    shape.closePath();
    const geom = new THREE.ShapeGeometry(shape);
    const mat = new THREE.MeshBasicMaterial({{color: 0x9b59b6, side: THREE.DoubleSide}});
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(n.x, n.y - 0.3, n.z);
    mesh.rotation.x = -Math.PI / 2;
    scene.add(mesh);
  }});

  // Dimension lines
  function addDimLine(x1, y1, z1, x2, y2, z2, label, offsetY) {{
    const points = [
      new THREE.Vector3(x1, y1 + offsetY, z1),
      new THREE.Vector3(x2, y2 + offsetY, z2)
    ];
    const geom = new THREE.BufferGeometry().setFromPoints(points);
    const mat = new THREE.LineDashedMaterial({{color: 0xaaaaaa, dashSize: 0.2, gapSize: 0.1}});
    const line = new THREE.Line(geom, mat);
    line.computeLineDistances();
    scene.add(line);

    const cx = (x1 + x2) / 2;
    const cy = (y1 + y2) / 2 + offsetY;
    const cz = (z1 + z2) / 2;
    const canvas = document.createElement('canvas');
    canvas.width = 256; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#aaa';
    ctx.font = '28px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(label, 128, 42);
    const tex = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({{map: tex}});
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(cx, cy, cz);
    sprite.scale.set(2.5, 0.6, 1);
    scene.add(sprite);
  }}

  // X dimension
  addDimLine(0, 0, -1, 10, 0, -1, '1000 cm (10 m)', 0);
  // Y dimensions
  addDimLine(-1, 0, 0, -1, 0, 7.25, '725 cm', 0);
  addDimLine(-1, 0, 7.25, -1, 0, 16.15, '890 cm', 0);
  addDimLine(-1, 0, 0, -1, 0, 16.15, '1615 cm', 0);
  // Z dimension
  addDimLine(11, 0, 0, 11, 3.56, 0, '356 cm', 0);

  // Mouse controls
  let isRotating = false;
  let isPanning = false;
  let prevMouse = {{x: 0, y: 0}};
  let spherical = new THREE.Spherical();
  spherical.setFromVector3(new THREE.Vector3().subVectors(camera.position, ORBIT_TARGET));

  renderer.domElement.addEventListener('mousedown', e => {{
    if (e.button === 0) isRotating = true;
    if (e.button === 2) isPanning = true;
    prevMouse = {{x: e.clientX, y: e.clientY}};
  }});
  renderer.domElement.addEventListener('mouseup', () => {{
    isRotating = false; isPanning = false;
  }});
  renderer.domElement.addEventListener('contextmenu', e => e.preventDefault());
  renderer.domElement.addEventListener('mousemove', e => {{
    const dx = e.clientX - prevMouse.x;
    const dy = e.clientY - prevMouse.y;
    prevMouse = {{x: e.clientX, y: e.clientY}};
    if (isRotating) {{
spherical.theta -= dx * 0.01;
      spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi - dy * 0.01));
      camera.position.copy(ORBIT_TARGET).add(new THREE.Vector3().setFromSpherical(spherical));
      camera.lookAt(ORBIT_TARGET);
    }}
    if (isPanning) {{
      const right = new THREE.Vector3();
      const up2 = new THREE.Vector3();
      camera.getWorldDirection(new THREE.Vector3());
      right.crossVectors(camera.up, camera.getWorldDirection(new THREE.Vector3())).normalize();
      up2.copy(camera.up);
      camera.position.addScaledVector(right, -dx * 0.02);
      camera.position.addScaledVector(up2, dy * 0.02);
    }}
  }});
  renderer.domElement.addEventListener('wheel', e => {{
    spherical.radius = Math.max(2, Math.min(100, spherical.radius + e.deltaY * 0.02));
    camera.position.copy(ORBIT_TARGET).add(new THREE.Vector3().setFromSpherical(spherical));
    camera.lookAt(ORBIT_TARGET);
  }});

  window.addEventListener('resize', () => {{
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }});

  window.addEventListener('keydown', (e) => {{
    if (e.key === 'n' || e.key === 'N') {{
      nodeGroup.visible = !nodeGroup.visible;
    }}
    if (e.key === 'e' || e.key === 'E') {{
      elementsGroup.visible = !elementsGroup.visible;
      axesGroup.visible = !elementsGroup.visible;
    }}
  }});

  function animate() {{
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }}
  animate();
</script>
</body>
</html>"""

    out_path = os.path.join(os.path.dirname(__file__), "..", "edificio_3d.html")

    # (P3) Regenerar NO debe perder el modo análisis: si el visor ya existe con
    # la integracion (analysis_map.js + pestanas), se actualizan solo los datos
    # de geometria (elements / nodesData / supportsSet) y se conserva el resto.
    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            prev = f.read()
        if "analysis_map.js" in prev:
            def _reemplazar(texto, patron, nuevo):
                nuevo_texto, n = re.subn(patron, lambda _m: nuevo, texto, flags=re.S)
                return nuevo_texto, n

            html, n1 = _reemplazar(
                prev, r"const elements = \[.*?\];", "const elements = " + elements_json + ";")
            html, n2 = _reemplazar(
                html, r"const nodesData = \[.*?\];",
                "const nodesData = " + nodes_json + ";")
            html, n3 = _reemplazar(
                html, r"const supportsSet = new Set\(\[.*?\]\);",
                "const supportsSet = new Set(" + supports_json + ");")
            if n1 and n2 and n3:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"HTML actualizado (geometria) en: {out_path}")
                print("  [P3] se conservaron el <script analysis_map.js>, la pestana "
                      "Diagramas y el panel DATOS del modo analisis.")
                return
            print("[aviso] No se pudieron localizar los bloques de geometria "
                  "(esperado en un visor parcial); se regenera la vista basica.")
            # continua con la generacion completa de abajo

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML generado: {out_path}")
    print("Abrilo en el navegador para ver el modelo 3D")

if __name__ == "__main__":
    main()

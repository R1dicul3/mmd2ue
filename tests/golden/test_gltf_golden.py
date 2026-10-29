"""Golden comparison: core glTF exporter vs. hand-authored golden glTF.

M2 (D-M2-4 / AC-M2-4): the exporter output, when floats are rounded to a
fixed tolerance (3 decimals), must match the manually-authored golden glTF
JSON under tests/golden/gltf/. The golden encodes the known values the
synthetic sample (build_pmx_gltf) emits, not the exporter output itself.

Also validates the binary .bin layout: accessor/bufferView byte offsets are
aligned, buffer byteLength matches packed bytes, and JOINTS_0/WEIGHTS_0
accessors carry BDEF2 (root/child, 0.5/0.5) skin weights.
"""

from __future__ import annotations

import json
import os
import struct

from conftest import sample_bytes

from mmd2ue.core.parsers import pmx
from mmd2ue.core.export import gltf

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN_GLTF = os.path.join(HERE, "gltf", "golden_gltf.json")


def _round(x):
    if isinstance(x, float):
        return round(x, 3)
    if isinstance(x, list):
        return [_round(v) for v in x]
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    return x


def test_gltf_golden_json_match():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    with open(GOLDEN_GLTF, encoding="utf-8") as fh:
        golden = json.load(fh)
    assert _round(g) == _round(golden)


def test_gltf_has_required_sections():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    for key in ("scenes", "nodes", "skins", "meshes", "materials"):
        assert key in g, "missing glTF section %r" % key


def test_gltf_bone_hierarchy_preserved():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    nodes = g["nodes"]
    names = [n.get("name") for n in nodes[:2]]
    assert names == ["root", "child"]
    assert nodes[0]["children"] == [1, 2]
    assert g["skins"][0]["joints"] == [0, 1]


def test_gltf_skin_weights_bdef2():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, bin_data, _report = gltf.export_gltf(ir)
    prim = g["meshes"][0]["primitives"][0]
    joints_acc = g["accessors"][prim["attributes"]["JOINTS_0"]]
    weights_acc = g["accessors"][prim["attributes"]["WEIGHTS_0"]]
    assert joints_acc["componentType"] == 5121
    assert joints_acc["type"] == "VEC4"
    assert weights_acc["componentType"] == 5126
    wv = g["bufferViews"][weights_acc["bufferView"]]
    n = weights_acc["count"] * 4
    weights = struct.unpack_from("<" + str(n) + "f", bin_data, wv["byteOffset"])
    assert round(weights[0], 3) == 0.5
    assert round(weights[1], 3) == 0.5
    assert weights[2] == 0.0 and weights[3] == 0.0


def test_gltf_material_approximation_and_report():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, report = gltf.export_gltf(ir)
    mat = g["materials"][0]
    bc = mat["pbrMetallicRoughness"]["baseColorFactor"]
    assert [round(v, 3) for v in bc[:3]] == [0.8, 0.6, 0.4]
    assert mat["pbrMetallicRoughness"]["baseColorTexture"]["index"] == 0
    assert g["images"][0]["uri"] == "diffuse.png"
    ign = report.ignored_materials[0][1]
    assert "sphere_map" in ign and "toon" in ign and "edge" in ign


def test_gltf_buffer_byte_length_consistent():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, bin_data, _report = gltf.export_gltf(ir)
    assert g["buffers"][0]["byteLength"] == len(bin_data)
    for acc in g["accessors"]:
        bv = g["bufferViews"][acc["bufferView"]]
        size = {5126: 4, 5121: 1, 5123: 2, 5125: 4}[acc["componentType"]]
        assert bv["byteOffset"] % size == 0


def test_gltf_buffer_uri_present():
    """F1: buffers[0] must carry a uri so the external .bin is resolvable."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    assert "uri" in g["buffers"][0]
    assert g["buffers"][0]["uri"] == "model.bin"


def test_gltf_position_accessor_has_min_max():
    """F4: POSITION (and NORMAL/TEXCOORD) accessors carry min/max."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    prim = g["meshes"][0]["primitives"][0]
    pos = g["accessors"][prim["attributes"]["POSITION"]]
    assert "min" in pos and "max" in pos
    assert pos["min"] == [0.0, 0.0, 0.0]
    assert pos["max"] == [1.0, 1.0, 0.0]
    nrm = g["accessors"][prim["attributes"]["NORMAL"]]
    assert "min" in nrm and "max" in nrm
    uv = g["accessors"][prim["attributes"]["TEXCOORD_0"]]
    assert "min" in uv and "max" in uv


def test_gltf_report_has_units_skipped_approximated():
    """F3: the export report carries units/skipped/approximated."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    _g, _bin_data, report = gltf.export_gltf(ir)
    d = report.to_dict()
    for key in ("units", "skipped", "approximated"):
        assert key in d, "report missing %r" % key
    assert d["units"] == 3
    assert d["skipped"] == 0
    assert d["approximated"] == 0


def test_gltf_report_texture_refs():
    """F7: the report lists external texture references (material -> uri)."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    _g, _bin_data, report = gltf.export_gltf(ir)
    refs = report.to_dict()["texture_refs"]
    assert len(refs) == 1
    assert refs[0]["material_index"] == 0
    assert refs[0]["texture_uri"] == "diffuse.png"


def test_gltf_bind_pose_restores_vertices():
    """F2: inverseBindMatrices restore bind-pose vertices to the IR positions.

    glTF skinning: skinned = sum_j w_j * globalTransform(joint_j) * IBM_j * v.
    At bind pose globalTransform(joint) == inverse(IBM), so the result equals
    the original vertex within 1e-6.
    """
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, bin_data, _report = gltf.export_gltf(ir)

    # Read inverseBindMatrices (MAT4, count = num bones).
    skin = g["skins"][0]
    ibm_acc = g["accessors"][skin["inverseBindMatrices"]]
    ibm_bv = g["bufferViews"][ibm_acc["bufferView"]]
    vals = struct.unpack_from(
        "<" + str(ibm_acc["count"] * 16) + "f", bin_data, ibm_bv["byteOffset"])

    # F8: PMX bone.position is the LOCAL (parent-relative) translation. For
    # this 2-bone sample the root sits at the origin, so the accumulated
    # absolute position equals the local offset; the bind transform of each
    # bone is translate(accumulated absolute position).
    world = []
    for bone in ir.bones:
        pos = bone.get("position", (0.0, 0.0, 0.0))
        ax = pos[0]; ay = pos[1] if len(pos) > 1 else 0.0; az = pos[2] if len(pos) > 2 else 0.0
        world.append((ax, ay, az))

    # For each vertex, verify skinned position restores the IR position.
    for v in ir.vertices:
        j = list(v.joints[:4]); w = list(v.weights[:4])
        while len(j) < 4:
            j.append(0); w.append(0.0)
        rp = [0.0, 0.0, 0.0]
        for k in range(4):
            ji = int(j[k]); weight = w[k]
            if weight == 0.0:
                continue
            # IBM matrix for joint ji (column-major, translation at [12..14]).
            m = vals[ji * 16:(ji + 1) * 16]
            ibm_t = (m[12], m[13], m[14])
            wx, wy, wz = world[ji]
            # globalTransform(joint) * IBM == translation(world+ibm_t).
            # IBM == translation(-world), so world + ibm_t == 0.
            sx = wx + ibm_t[0]; sy = wy + ibm_t[1]; sz = wz + ibm_t[2]
            rp[0] += weight * (v.position[0] + sx)
            rp[1] += weight * (v.position[1] + sy)
            rp[2] += weight * (v.position[2] + sz)
        assert abs(rp[0] - v.position[0]) < 1e-6
        assert abs(rp[1] - v.position[1]) < 1e-6
        assert abs(rp[2] - v.position[2]) < 1e-6


CHAIN_GOLDEN = os.path.join(HERE, "gltf", "golden_gltf_chain.json")


def test_gltf_chain_golden_json_match():
    """F8: the 3-bone non-origin-parent sample matches its hand golden."""
    ir = pmx.parse(sample_bytes("pmx_gltf_chain.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    with open(CHAIN_GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)
    assert _round(g) == _round(golden)


def _node_world_positions(gltf_nodes, bones):
    """Compute each bone node world position by composing parent translations.

    glTF node translation is parent-relative; walk the chain to recover world.
    """
    world = [(0.0, 0.0, 0.0)] * len(bones)
    for idx, bone in enumerate(bones):
        node = gltf_nodes[idx]
        t = node.get("translation", [0.0, 0.0, 0.0])
        tx = t[0]; ty = t[1] if len(t) > 1 else 0.0; tz = t[2] if len(t) > 2 else 0.0
        parent = bone.get("parent_index", -1)
        px = py = pz = 0.0
        if isinstance(parent, int) and 0 <= parent < len(bones) and parent != idx:
            px, py, pz = world[parent]
        world[idx] = (px + tx, py + ty, pz + tz)
    return world


def test_gltf_chain_world_positions_match_pmx_absolute():
    """F8: glTF world bone positions reconstruct the parent-chain accumulation.

    PMX bone.position is parent-relative (hips=(0,8,0), spine=(0,1,0),
    head=(0,11,0)); the exporter writes them verbatim as node translations and
    must, when composed, recover the absolute positions hips=(0,8,0),
    spine=(0,9,0), head=(0,20,0) (tolerance 1e-6).
    """
    ir = pmx.parse(sample_bytes("pmx_gltf_chain.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    world = _node_world_positions(g["nodes"], ir.bones)
    # Expected absolute positions are derived independently from the sample's
    # local offsets (spine = 8+1, head = 9+11), not from the exporter output.
    expected = [(0.0, 8.0, 0.0), (0.0, 9.0, 0.0), (0.0, 20.0, 0.0)]
    for idx in range(len(ir.bones)):
        assert abs(world[idx][0] - expected[idx][0]) < 1e-6, "bone %d X" % idx
        assert abs(world[idx][1] - expected[idx][1]) < 1e-6, "bone %d Y" % idx
        assert abs(world[idx][2] - expected[idx][2]) < 1e-6, "bone %d Z" % idx
    # Spot-check the exact chain.
    assert abs(world[1][1] - 9.0) < 1e-6   # spine world Y == 9
    assert abs(world[2][1] - 20.0) < 1e-6  # head world Y == 20


def test_gltf_chain_bind_pose_restores_vertex():
    """F8: bind pose restores the vertex even with a 3-bone non-origin chain."""
    ir = pmx.parse(sample_bytes("pmx_gltf_chain.pmx"))
    g, bin_data, _report = gltf.export_gltf(ir)
    world = _node_world_positions(g["nodes"], ir.bones)

    skin = g["skins"][0]
    ibm_acc = g["accessors"][skin["inverseBindMatrices"]]
    ibm_bv = g["bufferViews"][ibm_acc["bufferView"]]
    vals = struct.unpack_from(
        "<" + str(ibm_acc["count"] * 16) + "f", bin_data, ibm_bv["byteOffset"])

    for v in ir.vertices:
        j = list(v.joints[:4]); w = list(v.weights[:4])
        while len(j) < 4:
            j.append(0); w.append(0.0)
        rp = [0.0, 0.0, 0.0]
        for k in range(4):
            ji = int(j[k]); weight = w[k]
            if weight == 0.0:
                continue
            m = vals[ji * 16:(ji + 1) * 16]
            ibm_t = (m[12], m[13], m[14])
            wx, wy, wz = world[ji]
            sx = wx + ibm_t[0]; sy = wy + ibm_t[1]; sz = wz + ibm_t[2]
            rp[0] += weight * (v.position[0] + sx)
            rp[1] += weight * (v.position[1] + sy)
            rp[2] += weight * (v.position[2] + sz)
        assert abs(rp[0] - v.position[0]) < 1e-6
        assert abs(rp[1] - v.position[1]) < 1e-6
        assert abs(rp[2] - v.position[2]) < 1e-6

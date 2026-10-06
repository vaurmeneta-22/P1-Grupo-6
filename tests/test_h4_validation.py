import copy
import importlib.util
import json
import os
import tempfile
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "verificar_h4", os.path.join(REPO, "scripts", "verificar_h4.py"))
H4 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H4)


class H4ContractValidationTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(REPO, "Edificio.json"), encoding="utf-8") as stream:
            self.model = copy.deepcopy(json.load(stream))
        col = next(e for e in self.model["elements"] if e["id"] == 66)
        col.update(section="40x40", b=40.0, h=40.0)

    def validate(self, model):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as stream:
            json.dump(model, stream)
            path = stream.name
        try:
            return H4.validate_model(path)
        finally:
            os.unlink(path)

    def test_validates_case_a_beam_section(self):
        model = copy.deepcopy(self.model)
        beam = next(e for e in model["elements"] if e["id"] == 147)
        beam.update(section="50x75", b=50.0, h=75.0)
        result = self.validate_case(model, "A")
        self.assertEqual(result["element"], 147)
        self.assertEqual(result["section_cm"], [50, 75])

    def test_validates_case_b_pinned_support(self):
        model = copy.deepcopy(self.model)
        support = next(s for s in model["supports"] if s["node"] == 1)
        support.update(type="pinned", DOF=[1, 1, 1, 0, 0, 0])
        result = self.validate_case(model, "B")
        self.assertEqual(result["support_node"], 1)
        support["DOF"] = [1, 1, 0, 0, 0, 0]
        with self.assertRaisesRegex(ValueError, "articulado"):
            self.validate_case(model, "B")

    def validate_case(self, model, case_id):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as stream:
            json.dump(model, stream)
            path = stream.name
        try:
            return H4.validate_model(path, case_id)
        finally:
            os.unlink(path)

    def test_valid_case_c_contract_includes_surface_slabs(self):
        result = self.validate(self.model)
        self.assertEqual(result["element"], 66)
        self.assertEqual(result["section_cm"], [40, 40])

    def test_rejects_nonpositive_structural_section(self):
        col = next(e for e in self.model["elements"] if e["id"] == 66)
        col["b"] = 0
        with self.assertRaisesRegex(ValueError, "positivo"):
            self.validate(self.model)

    def test_rejects_duplicate_element_ids(self):
        self.model["elements"].append(copy.deepcopy(self.model["elements"][0]))
        with self.assertRaisesRegex(ValueError, "duplicados"):
            self.validate(self.model)

    def test_compares_solver_outputs_with_declared_tolerance(self):
        old_results = H4.RESULTS
        with tempfile.TemporaryDirectory() as folder:
            H4.RESULTS = folder
            sample = {"element_forces_global": {"66": {"i": [1.0, 2.0]}},
                      "displacements_m": {"13": [0.001]},
                      "reactions_kN": {"13": [5.0]}, "summary": {"ok": True},
                      "verifications": {"equilibrio_error": 1e-12}}
            for tag, delta in (("left", 0.0), ("right", 1e-10)):
                result = copy.deepcopy(sample)
                result["element_forces_global"]["66"]["i"][0] += delta
                with open(H4.result_path(tag, "G"), "w", encoding="utf-8") as stream:
                    json.dump(result, stream)
            self.assertTrue(H4.compare("G", "left", "right")["pass"])
        H4.RESULTS = old_results

    def test_builds_case_comparison_highlights(self):
        old_results = H4.RESULTS
        with tempfile.TemporaryDirectory() as folder:
            H4.RESULTS = folder
            top = str(next(e for e in self.model["elements"] if e["id"] == 66)["node_j"])
            for tag, offset in (("modC", 0.0), ("h4_direct", 1e-10)):
                result = {"summary": {"Carga_G_total_kN": 1200.0 + offset},
                          "element_forces_global": {"66": {"local_i": [100.0, 2, 3, 4, 5.0 + offset, 6.0]}},
                          "displacements_m": {top: [0.003, 0.004, 0.0]}}
                with open(H4.result_path(tag, "G"), "w", encoding="utf-8") as stream:
                    json.dump(result, stream)
            row = H4.comparison_row("G", {"pass": True, "max_abs_difference": 0.0})
            self.assertEqual(row["case_name"], "G")
            self.assertAlmostEqual(row["unity"]["disp_mm"], 5.0)
            self.assertAlmostEqual(row["delta"]["my_kNm"], 1e-10)
            self.assertTrue(row["pass"])
        H4.RESULTS = old_results


if __name__ == "__main__":
    unittest.main()

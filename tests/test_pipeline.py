"""Run with:  python3 -m unittest discover -s tests -v"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import pipeline as P

ADVERT = ("Senior AI Engineer to lead our agent platform. Python and TypeScript. "
          "LangChain and vector databases expected. AWS. Eight years. "
          "London, three days a week in the office.")


class Stage1Receive(unittest.TestCase):
    def test_normal_input_passes(self):
        state, rec = P.receive({"advert": ADVERT})
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["stage"], 1)

    def test_empty_input_is_refused(self):
        state, rec = P.receive({"advert": "   "})
        self.assertFalse(rec["ok"])
        self.assertIn("nothing", rec["detail"])

    def test_oversized_input_is_refused(self):
        state, rec = P.receive({"advert": "x" * (config.MAX_INPUT_CHARS + 1)})
        self.assertFalse(rec["ok"])
        self.assertIn("limit", rec["detail"])

    def test_input_exactly_at_the_limit_passes(self):
        state, rec = P.receive({"advert": "x" * config.MAX_INPUT_CHARS})
        self.assertTrue(rec["ok"])


class Stage2Retrieve(unittest.TestCase):
    def test_knowledge_loads_and_is_chunked(self):
        ps = P.load_knowledge()
        self.assertGreater(len(ps), 5)
        for p in ps:
            self.assertTrue(p["id"] and p["heading"] and p["text"])

    def test_only_allowed_files_are_read(self):
        ps = P.load_knowledge()
        files = {p["file"] for p in ps}
        self.assertEqual(files, set(config.KNOWLEDGE_FILES))
        self.assertNotIn("mlops.md", files)

    def test_switching_a_file_on_changes_what_is_available(self):
        before = len(P.load_knowledge())
        after = len(P.load_knowledge(config.KNOWLEDGE_FILES + ["mlops.md"]))
        self.assertGreater(after, before)

    def test_a_missing_file_does_not_crash(self):
        ps = P.load_knowledge(["does_not_exist.md"])
        self.assertEqual(ps, [])

    def test_relevant_advert_retrieves_something(self):
        state, rec = P.retrieve({"advert": ADVERT, "ok": True})
        self.assertTrue(rec["ok"])
        self.assertGreater(len(rec["passages"]), 0)

    def test_floor_can_drop_everything(self):
        saved = config.RELEVANCE_FLOOR
        config.RELEVANCE_FLOOR = 0.99
        try:
            state, rec = P.retrieve({"advert": ADVERT, "ok": True})
            self.assertEqual(len(rec["passages"]), 0)
        finally:
            config.RELEVANCE_FLOOR = saved

    def test_passage_count_is_capped(self):
        saved = config.PASSAGES
        config.PASSAGES = 1
        try:
            state, rec = P.retrieve({"advert": ADVERT, "ok": True})
            self.assertLessEqual(len(rec["passages"]), 1)
        finally:
            config.PASSAGES = saved

    def test_scores_are_ordered(self):
        state, rec = P.retrieve({"advert": ADVERT, "ok": True})
        scores = [p["score"] for p in rec["passages"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_long_passage_cannot_win_on_length_alone(self):
        q = P.terms("python")
        short = P.score_passage(q, P.terms("python"))
        long = P.score_passage(q, P.terms("python " + "filler " * 80))
        self.assertGreater(short, long)


class Stage3BuildPrompt(unittest.TestCase):
    def test_retrieved_notes_reach_the_prompt(self):
        state = {"advert": ADVERT, "ok": True}
        state, _ = P.retrieve(state)
        state, rec = P.build_prompt(state)
        self.assertIn("REFERENCE NOTES", state["system"])
        self.assertGreater(rec["estimated_tokens"], 0)

    def test_no_notes_means_an_explicit_instruction_not_to_invent(self):
        state = {"advert": ADVERT, "ok": True, "passages": []}
        state, rec = P.build_prompt(state)
        self.assertIn("rather than inventing", state["system"])

    def test_more_passages_costs_more_tokens(self):
        saved = config.PASSAGES
        try:
            config.PASSAGES = 1
            s1 = {"advert": ADVERT, "ok": True}
            s1, _ = P.retrieve(s1); s1, r1 = P.build_prompt(s1)
            config.PASSAGES = 4
            s2 = {"advert": ADVERT, "ok": True}
            s2, _ = P.retrieve(s2); s2, r2 = P.build_prompt(s2)
            self.assertGreater(r2["estimated_tokens"], r1["estimated_tokens"])
        finally:
            config.PASSAGES = saved

    def test_the_advert_is_in_the_user_message(self):
        state = {"advert": ADVERT, "ok": True, "passages": []}
        state, _ = P.build_prompt(state)
        self.assertIn(ADVERT[:40], state["user"])


class Stage4CallModel(unittest.TestCase):
    def test_demo_mode_needs_no_key(self):
        state = {"advert": ADVERT, "ok": True, "passages": []}
        state, _ = P.build_prompt(state)
        state, rec = P.call_model(state, api_key=None)
        self.assertEqual(rec["mode"], "demo")
        self.assertIn("seniority", state["answer"])

    def test_demo_mode_is_deterministic(self):
        s = {"advert": ADVERT, "ok": True, "passages": []}
        self.assertEqual(P.demo_model(s), P.demo_model(s))

    def test_parse_clean_json(self):
        d, p = P.parse_reply('{"seniority":"mid"}')
        self.assertEqual(d["seniority"], "mid")
        self.assertIsNone(p)

    def test_parse_code_fence(self):
        d, _ = P.parse_reply('```json\n{"seniority":"mid"}\n```')
        self.assertEqual(d["seniority"], "mid")

    def test_parse_chatty_model(self):
        d, p = P.parse_reply('Sure!\n{"seniority":"mid"}\nHope that helps.')
        self.assertEqual(d["seniority"], "mid")
        self.assertIn("text around", p)

    def test_parse_rubbish(self):
        d, p = P.parse_reply("I cannot help with that.")
        self.assertIsNone(d)
        self.assertIn("no JSON", p)

    def test_parse_empty(self):
        d, p = P.parse_reply("")
        self.assertIsNone(d)


class Stage5Check(unittest.TestCase):
    def good(self):
        return {"ok": True, "passages": [],
                "answer": {"role": "AI Engineer", "seniority": "mid",
                           "work_mode": "remote", "key_skills": ["Python"],
                           "jargon_explained": ""}}

    def test_a_good_answer_passes(self):
        state, rec = P.check(self.good())
        self.assertTrue(rec["ok"])

    def test_banned_phrase_is_caught(self):
        s = self.good()
        s["answer"]["jargon_explained"] = "As an AI, I would say..."
        state, rec = P.check(s)
        self.assertFalse(rec["ok"])
        self.assertTrue(any("banned" in f for f in rec["failures"]))

    def test_value_outside_the_allowed_list_is_caught(self):
        s = self.good()
        s["answer"]["seniority"] = "Senior Engineer II"
        state, rec = P.check(s)
        self.assertFalse(rec["ok"])

    def test_bad_work_mode_is_caught(self):
        s = self.good()
        s["answer"]["work_mode"] = "flexible"
        state, rec = P.check(s)
        self.assertFalse(rec["ok"])

    def test_grounding_check_is_off_by_default(self):
        self.assertFalse(config.REQUIRE_GROUNDING)

    def test_grounding_catches_an_invented_explanation(self):
        saved = config.REQUIRE_GROUNDING
        config.REQUIRE_GROUNDING = True
        try:
            s = self.good()
            s["passages"] = [{"id": "x", "heading": "h",
                              "text": "Retrieval means finding passages first."}]
            s["answer"]["jargon_explained"] = (
                "Quantum entanglement powers blockchain neural substrates "
                "throughout distributed holographic lattices.")
            state, rec = P.check(s)
            self.assertFalse(rec["ok"])
            self.assertTrue(any("grounded" in f for f in rec["failures"]))
        finally:
            config.REQUIRE_GROUNDING = saved

    def test_grounding_passes_a_real_explanation(self):
        saved = config.REQUIRE_GROUNDING
        config.REQUIRE_GROUNDING = True
        try:
            s = self.good()
            s["passages"] = [{"id": "x", "heading": "h", "text":
                              "Retrieval means finding relevant passages first "
                              "and putting them in front of the model."}]
            s["answer"]["jargon_explained"] = (
                "Retrieval means finding relevant passages before the model answers.")
            state, rec = P.check(s)
            self.assertTrue(rec["ok"], rec["detail"])
        finally:
            config.REQUIRE_GROUNDING = saved


class WholePipeline(unittest.TestCase):
    def test_all_five_stages_run(self):
        r = P.run(ADVERT)
        self.assertTrue(r["ok"])
        self.assertEqual([t["stage"] for t in r["trace"]], [1, 2, 3, 4, 5])
        self.assertEqual([t["name"] for t in r["trace"]],
                         ["receive", "retrieve", "build_prompt",
                          "call_model", "check"])

    def test_it_stops_at_the_stage_that_failed(self):
        r = P.run("")
        self.assertFalse(r["ok"])
        self.assertEqual(len(r["trace"]), 1)
        self.assertIsNone(r["answer"])

    def test_every_stage_is_timed(self):
        r = P.run(ADVERT)
        for t in r["trace"]:
            self.assertIsInstance(t["ms"], float)

    def test_trace_can_be_switched_off(self):
        saved = config.SHOW_TRACE
        config.SHOW_TRACE = False
        try:
            self.assertIsNone(P.run(ADVERT)["trace"])
        finally:
            config.SHOW_TRACE = saved

    def test_thirty_adverts_all_complete(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ads = json.load(open(os.path.join(here, "data", "adverts.json")))
        self.assertEqual(len(ads), 30)
        for a in ads:
            r = P.run(a["body"])
            self.assertTrue(r["ok"], f"{a['id']} failed: {r.get('refusal')}")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class WhenThingsGoWrong(unittest.TestCase):
    """The failure modes a participant will actually hit."""

    def _with_failing_call(self, exc):
        """Swap the network call for one that always fails."""
        original = P.call_groq

        def boom(*a, **kw):
            raise exc
        P.call_groq = boom
        self.addCleanup(lambda: setattr(P, "call_groq", original))

    def test_a_rejected_key_does_not_crash_the_service(self):
        self._with_failing_call(
            P.ModelUnavailable("the model API rejected the key (401)."))
        r = P.run(ADVERT, api_key="gsk_wrong")
        self.assertFalse(r["ok"])
        self.assertIn("rejected the key", r["refusal"])

    def test_a_rejected_key_still_reports_the_stages_that_worked(self):
        self._with_failing_call(P.ModelUnavailable("rejected"))
        r = P.run(ADVERT, api_key="gsk_wrong")
        self.assertEqual(len(r["trace"]), 4)
        self.assertTrue(all(t["ok"] for t in r["trace"][:3]))
        self.assertFalse(r["trace"][3]["ok"])

    def test_an_unreachable_api_gives_an_explanation_not_a_stack_trace(self):
        self._with_failing_call(
            P.ModelUnavailable("could not reach the model API: timed out."))
        r = P.run(ADVERT, api_key="gsk_whatever")
        self.assertFalse(r["ok"])
        self.assertIn("could not reach", r["refusal"])
        self.assertNotIn("Traceback", r["refusal"])

    def test_demo_mode_is_unaffected_by_any_of_this(self):
        self._with_failing_call(P.ModelUnavailable("should never be called"))
        r = P.run(ADVERT, api_key=None)
        self.assertFalse(r["ok"])
        self.assertEqual(len(r["trace"]), 5)

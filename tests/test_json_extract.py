from wiggum.json_extract import extract_last_fenced_json


class TestExtractLastFencedJson:
    def test_single_block(self):
        text = 'Some text\n```json\n{"status": "complete"}\n```\nMore text'
        assert extract_last_fenced_json(text) == {"status": "complete"}

    def test_multiple_blocks_returns_last(self):
        text = (
            '```json\n{"status": "in_progress"}\n```\n'
            "middle\n"
            '```json\n{"status": "complete"}\n```\n'
        )
        assert extract_last_fenced_json(text) == {"status": "complete"}

    def test_no_fenced_block(self):
        assert extract_last_fenced_json("no json here") is None

    def test_empty_string(self):
        assert extract_last_fenced_json("") is None

    def test_malformed_json(self):
        text = "```json\n{bad json}\n```"
        assert extract_last_fenced_json(text) is None

    def test_json_outside_fence_ignored(self):
        text = 'The response is {"status": "complete"} as shown above.'
        assert extract_last_fenced_json(text) is None

    def test_non_json_fenced_block_ignored(self):
        text = '```python\nprint("hello")\n```'
        assert extract_last_fenced_json(text) is None

    def test_nested_content(self):
        text = (
            '```json\n{"tasks": [{"id": 1, "done": true}], "status": "complete"}\n```'
        )
        result = extract_last_fenced_json(text)
        assert result == {"tasks": [{"id": 1, "done": True}], "status": "complete"}

    def test_multiline_json(self):
        text = (
            '```json\n{\n  "status": "complete",\n  "reason": "all tasks done"\n}\n```'
        )
        result = extract_last_fenced_json(text)
        assert result == {"status": "complete", "reason": "all tasks done"}

    def test_non_dict_json_returns_none(self):
        text = "```json\n[1, 2, 3]\n```"
        assert extract_last_fenced_json(text) is None

    def test_fenced_block_among_reasoning(self):
        text = (
            "I will now produce the status.\n"
            "The plan looks complete because all steps are done.\n"
            '```json\n{"status": "complete"}\n```\n'
            "That concludes the plan phase."
        )
        assert extract_last_fenced_json(text) == {"status": "complete"}

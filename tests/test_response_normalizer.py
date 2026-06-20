import unittest
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from agent.brain.response_normalizer import (
    coerce_message_text,
    sanitize_final_text,
    extract_urls,
    cap_visible_links,
    looks_like_not_found,
)

class TestResponseNormalizer(unittest.TestCase):
    def test_coerce_message_text_string(self):
        self.assertEqual(coerce_message_text("hello"), "hello")
        self.assertEqual(coerce_message_text(None), "")

    def test_coerce_message_text_list(self):
        content = [
            "Hello",
            {"type": "text", "text": " World"},
            {"text": "!"}
        ]
        self.assertEqual(coerce_message_text(content), "Hello\n World\n!")

    def test_sanitize_final_text(self):
        # Should strip <think> blocks
        input_text = "<think>some thoughts</think>Hello there!"
        self.assertEqual(sanitize_final_text(input_text), "Hello there!")

        # Should format markdown links to link text: url format
        link_text = "Check out [Google](https://google.com) here"
        self.assertEqual(sanitize_final_text(link_text), "Check out Google: https://google.com here")

        # Should remove formatting like bold/code ticks
        fmt_text = "**Bold** and `code` symbols."
        self.assertEqual(sanitize_final_text(fmt_text), "Bold and code symbols.")

    def test_extract_urls(self):
        text = "Hello https://google.com and http://example.org/path?query=1."
        self.assertEqual(extract_urls(text), ["https://google.com", "http://example.org/path?query=1"])

    def test_cap_visible_links(self):
        text = (
            "Link 1: https://link1.com\n"
            "Link 2: https://link2.com\n"
            "Link 3: https://link3.com\n"
            "Link 4: https://link4.com"
        )
        # Should cap to 3 links, which removes the line containing link4 if it's over the limit
        capped = cap_visible_links(text, limit=3)
        self.assertIn("https://link3.com", capped)
        self.assertNotIn("https://link4.com", capped)

    def test_looks_like_not_found(self):
        self.assertTrue(looks_like_not_found("không tìm thấy sự kiện nào"))
        self.assertTrue(looks_like_not_found("khong co ket qua nao"))
        self.assertFalse(looks_like_not_found("đã tìm thấy 2 sự kiện"))

if __name__ == "__main__":
    unittest.main()

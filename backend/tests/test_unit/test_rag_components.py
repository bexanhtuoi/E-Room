from __future__ import annotations

from app.rag.chunking import TextChunker
from app.utils.file_handle import (
    delete_path,
    ensure_dir,
    file_size,
    list_files,
    safe_filename,
    sha256_hex,
)


class TestTextChunker:
    def test_chunk_text_empty(self):
        chunker = TextChunker(chunk_size=100)
        assert chunker.chunk_text("") == []

    def test_chunk_text_whitespace_only(self):
        chunker = TextChunker()
        assert chunker.chunk_text("   \n\n  ") == []

    def test_chunk_text_short_text(self):
        chunker = TextChunker(chunk_size=500)
        result = chunker.chunk_text("Hello world, this is a short text.")
        assert len(result) == 1
        assert "Hello world" in result[0]

    def test_chunk_text_long_text(self):
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "This is a long text that should be split into multiple chunks. " * 20
        result = chunker.chunk_text(text)
        assert len(result) > 1

    def test_chunk_text_with_markdown_headers(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "# Introduction\n\nThis is the intro.\n\n# Body\n\nThis is the body section."
        result = chunker.chunk_text(text)
        assert len(result) >= 1

    def test_chunk_size_respected(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=0)
        text = "word " * 100
        result = chunker.chunk_text(text)
        for chunk in result:
            assert len(chunk) <= 150

    def test_chunker_custom_separators(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20, separators=["\n", " "])
        text = "line one\nline two\nline three"
        result = chunker.chunk_text(text)
        assert len(result) >= 1

    def test_chunker_unicode_content(self):
        chunker = TextChunker()
        text = "Xin chào thế giới! 你好世界! Hello world!"
        result = chunker.chunk_text(text)
        assert len(result) >= 1
        assert "Xin chào" in result[0]

    def test_chunk_text_deterministic(self):
        chunker = TextChunker(chunk_size=100)
        text = "This is a test for deterministic chunking behaviour."
        r1 = chunker.chunk_text(text)
        r2 = chunker.chunk_text(text)
        assert r1 == r2

    def test_chunk_empty_after_strip(self):
        chunker = TextChunker()
        assert chunker.chunk_text("   \n   \t  ") == []


class TestFileHandle:
    def test_safe_filename_removes_special_chars(self):
        result = safe_filename('hello:world/test*file')
        assert "/" not in result
        assert ":" not in result
        assert "*" not in result

    def test_safe_filename_keeps_valid_chars(self):
        result = safe_filename("hello-world.txt")
        assert result == "hello-world.txt"

    def test_safe_filename_unicode(self):
        result = safe_filename("tài liệu.txt")
        assert result == "tài liệu.txt"

    def test_sha256_hex_string(self):
        h = sha256_hex("hello")
        assert len(h) == 64
        assert h == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_sha256_hex_bytes(self):
        h = sha256_hex(b"hello")
        assert len(h) == 64

    def test_sha256_hex_empty(self):
        h = sha256_hex("")
        assert len(h) == 64

    def test_sha256_hex_unicode(self):
        h = sha256_hex("xin chào")
        assert len(h) == 64

    def test_ensure_dir_creates_directory(self, tmp_path):
        test_dir = tmp_path / "test_dir"
        assert not test_dir.exists()

        result = ensure_dir(str(test_dir))
        assert test_dir.exists()
        assert result == test_dir

    def test_ensure_dir_existing(self, tmp_path):
        test_dir = tmp_path / "existing"
        test_dir.mkdir()
        assert ensure_dir(str(test_dir)) == test_dir

    def test_ensure_dir_nested(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        result = ensure_dir(str(nested))
        assert nested.exists()

    def test_file_size_returns_bytes(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert file_size(str(f)) == 5

    def test_list_files_glob(self, tmp_path):
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        (tmp_path / "c.txt").write_text("")
        files = list_files(str(tmp_path), "*.py")
        assert len(files) == 2

    def test_list_files_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.py").write_text("")
        files = list_files(str(tmp_path), "*.py", recursive=True)
        assert len(files) == 1

    def test_list_files_not_directory(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("")
        assert list_files(str(f)) == []

    def test_delete_path_file(self, tmp_path):
        f = tmp_path / "to_delete.txt"
        f.write_text("data")
        assert delete_path(str(f))
        assert not f.exists()

    def test_delete_path_missing_ok_true(self, tmp_path):
        assert delete_path(str(tmp_path / "missing.txt"))

    def test_delete_path_directory(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        (d / "file.txt").write_text("")
        assert delete_path(str(d))
        assert not d.exists()

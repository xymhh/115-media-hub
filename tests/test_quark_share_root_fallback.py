# -*- coding: utf-8 -*-
"""夸克分享根目录读取回归测试。

真机现象：部分夸克分享的根目录（``pdir_fid=0``）返回空 ``list``，服务端要求按
``share.first_fid`` 再查一次才有内容；旧逻辑把空列表当最终结果，前端表现为
「分享根目录的文件读不出来」。
"""
import unittest
from unittest import mock

from app.providers import quark


def _entry(fid: str, name: str, *, is_dir: bool = False) -> dict:
    return {
        "fid": fid,
        "file_name": name,
        "dir": bool(is_dir),
        "file_type": 0 if is_dir else 1,
        "size": 0 if is_dir else 1024,
        "pdir_fid": "0",
    }


class TestQuarkShareRootFallback(unittest.TestCase):
    def test_root_empty_list_retries_with_first_fid(self):
        calls = []

        def _fake_request(url, headers, timeout=45, fallback=""):
            calls.append(url)
            if "pdir_fid=0" in url:
                return {
                    "status": 200,
                    "code": 0,
                    "data": {
                        "list": [],
                        "share": {"pwd_id": "pwd1", "first_fid": "fid-root"},
                    },
                }
            return {
                "status": 200,
                "code": 0,
                "data": {"list": [_entry("f1", "根目录文件.mkv")], "share": {"pwd_id": "pwd1"}},
            }

        with mock.patch.object(quark, "_request_quark_json", side_effect=_fake_request):
            payload = quark._list_quark_share_page(
                "cookie", "pwd1", "stoken-a", "0", force_refresh=True
            )

        self.assertEqual(len(calls), 2, "根目录为空时必须按 first_fid 补查一次")
        self.assertIn("pdir_fid=fid-root", calls[1])
        self.assertEqual([e["name"] for e in payload["entries"]], ["根目录文件.mkv"])
        self.assertEqual(payload["entries"][0]["id"], "f1")

    def test_non_empty_root_does_not_retry(self):
        calls = []

        def _fake_request(url, headers, timeout=45, fallback=""):
            calls.append(url)
            return {
                "status": 200,
                "code": 0,
                "data": {
                    "list": [_entry("f2", "直接就在根目录.mp4")],
                    "share": {"pwd_id": "pwd1", "first_fid": "fid-root"},
                },
            }

        with mock.patch.object(quark, "_request_quark_json", side_effect=_fake_request):
            payload = quark._list_quark_share_page(
                "cookie", "pwd1", "stoken-b", "0", force_refresh=True
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(payload["entries"]), 1)

    def test_sub_directory_is_never_retried(self):
        calls = []

        def _fake_request(url, headers, timeout=45, fallback=""):
            calls.append(url)
            return {
                "status": 200,
                "code": 0,
                "data": {"list": [], "share": {"pwd_id": "pwd1", "first_fid": "fid-root"}},
            }

        with mock.patch.object(quark, "_request_quark_json", side_effect=_fake_request):
            payload = quark._list_quark_share_page(
                "cookie", "pwd1", "stoken-c", "fid-sub", force_refresh=True
            )

        self.assertEqual(len(calls), 1, "子目录为空就是真空，不能回退到 first_fid")
        self.assertEqual(payload["entries"], [])


if __name__ == "__main__":
    unittest.main()

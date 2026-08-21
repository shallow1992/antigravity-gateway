# Issue #5: [Security] パストラバーサル判定の厳密化 (Path.is_relative_to)

## 📌 概要
`src/security.py` の `is_safe_file_path` において、パスの包含関係を文字列比較（`str(target).startswith(str(root))`）で行っている部分を、Python 3.9+ の標準機能 `Path.is_relative_to()` に置き換えてより厳密にする。

## 🎯 目的
パスの区切り文字や末尾スラッシュの差異による誤判定を防ぎ、パストラバーサル防御の堅牢性を高める。

## 🔍 現状の課題
- 文字列比較だと、例えば `/workspace_fake/file` が `/workspace` で `startswith` 判定に誤ってパスしてしまうようなエッジケース（境界プレフィックス問題）の可能性がある。

## 🛠️ 修正方針
1. `src/security.py` の `is_safe_file_path` を更新：
   ```python
   # Before:
   if not str(target).startswith(str(root)):
       return False

   # After:
   if not target.is_relative_to(root):
       return False
   ```
2. 単体テストでプレフィックス境界のテストケースを追加。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] `target.is_relative_to(root)` を用いた厳密な包含判定になっていること
- [ ] 境界プレフィックスの単体テストが追加され PASS すること

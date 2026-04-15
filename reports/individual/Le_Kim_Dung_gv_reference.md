# Báo cáo cá nhân — mẫu GV (reference)

**Họ và tên:** Lê Kim Dũng  
**Vai trò:** Embed & Idempotency Owner · Cleaning & Quality Owner · Monitoring / Docs Owner  
**Độ dài:** ~500 từ

---

## 1. Phụ trách

Tôi chịu trách nhiệm chính cho ba mảng trong pipeline Day 10:

- **Cleaning rules mở rộng** (`transform/cleaning_rules.py`): Triển khai rule R7 (strip leftover `[cleaned:...]` tags chống tag accumulation khi re-ingest), R8 (quarantine chunk chứa migration/debug notes như "bản sync cũ", "lỗi migration"), và R9 (validate `exported_at` ISO datetime format — quarantine nếu không parse được).
- **Expectation suite mở rộng** (`quality/expectations.py`): Triển khai E7 (`no_migration_notes_in_cleaned`, severity halt — chặn pipeline nếu chunk migration note lọt vào cleaned) và E8 (`exported_at_within_30d`, severity warn — cảnh báo dữ liệu export cũ hơn 30 ngày).
- **Embed & Idempotency**: Đảm bảo ChromaDB collection `day10_kb` luôn là snapshot cleaned hiện tại qua cơ chế upsert `chunk_id` + prune stale IDs (`prev_ids - set(ids)` → `col.delete(ids=drop)`).
- **Monitoring & Documentation**: Hoàn thiện `docs/pipeline_architecture.md`, `docs/data_contract.md`, `docs/runbook.md`, `docs/quality_report.md`. Tạo file `data/raw/policy_export_corrupted.csv` cho Sprint 3 inject.

**Bằng chứng:** Cleaning rules R7/R8/R9 có docstring ghi `metric_impact` trong `cleaning_rules.py` (line 7–13). Artifact: `artifacts/eval/eval_combined_scenarios.csv`, `artifacts/logs/run_corrupted.log`, `artifacts/logs/run_clean.log`, `artifacts/manifests/manifest_clean.json`.

---

## 2. Quyết định kỹ thuật

**Thiết kế file corruption có chủ đích (`policy_export_corrupted.csv`):** Thay vì chỉ dùng flag `--no-refund-fix`, tôi tạo file corrupted riêng: (1) bỏ migration note khỏi chunk "14 ngày" → chunk stale lọt qua R8, (2) sửa `effective_date` HR cũ "10 ngày" thành `2026-02-01` → lọt qua date filter nhưng nội dung vẫn sai. Lý do: corruption thực tế thường **không có dấu hiệu rõ ràng** — dữ liệu "trông sạch" nhưng nội dung lỗi thời. Cách này chứng minh rằng chỉ filter theo metadata (`effective_date`, `doc_id`) là không đủ — cần expectation content-level (E3 kiểm "14 ngày", E6 kiểm "10 ngày phép năm").

**Halt vs warn cho E7 (migration notes):** Chọn **halt** vì migration note lọt vào cleaned → LLM trả lời kèm noise nội bộ ("bản sync cũ") → giảm `faithfulness` nghiêm trọng, user mất niềm tin. E8 (exported_at > 30 ngày) chọn **warn** vì dữ liệu cũ vẫn có giá trị tham khảo, chỉ cần cảnh báo cho team re-export.

---

## 3. Sự cố / anomaly

**Triệu chứng:** Sau pipeline corrupted (`--no-refund-fix --skip-validate`), eval cho `q_refund_window` có `hits_forbidden=yes` — top-1 trả chunk "14 ngày làm việc". Song song, `q_leave_version` cũng `hits_forbidden=yes` — top-k chứa "10 ngày phép năm" xung đột với policy 2026 (12 ngày).

**Nguyên nhân:** Khi bỏ prune giữa 2 run, vector cũ từ run corrupted vẫn tồn tại trong ChromaDB. Dù cleaned đã sạch ở run sau, `grading_run.jsonl` vẫn báo `hits_forbidden=true` do top-k query trả chunk từ run cũ.

**Fix:** Chạy lại pipeline chuẩn `python etl_pipeline.py run --run-id clean` — prune tự động xóa 6 IDs cũ (2 chunk lỗi + 4 chunk khác hash do text thay đổi), upsert 5 chunk sạch. Log: `embed_prune_removed=6`, `embed_upsert count=5`. Eval lại: `eval_clean.csv` tất cả `hits_forbidden=no`. Delta: `cleaned_records` 7 → 5, `quarantine_records` 3 → 5.

---

## 4. Before/after

**Log trước (run_id=corrupted):**

```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
expectation[hr_leave_no_stale_10d_annual] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed
embed_upsert count=7 collection=day10_kb
```

**Log sau (run_id=clean):**

```
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
expectation[hr_leave_no_stale_10d_annual] OK (halt) :: violations=0
embed_prune_removed=6
embed_upsert count=5 collection=day10_kb
PIPELINE_OK
```

**CSV eval (`eval_combined_scenarios.csv`):**

| scenario | question_id | hits_forbidden |
|----------|-------------|----------------|
| corrupted | q_refund_window | **yes** ❌ |
| corrupted | q_leave_version | **yes** ❌ |
| clean | q_refund_window | no ✅ |
| clean | q_leave_version | no ✅ |

---

## 5. Cải tiến thêm 2 giờ

Đọc cutoff HR `2026-01-01` từ `contracts/data_contract.yaml` (`policy_versioning.hr_leave_min_effective_date`) thay vì hard-code trong `cleaning_rules.py` (hướng Distinction d). Đồng thời triển khai freshness check ở **2 boundary** (ingest + publish): ghi thêm `ingest_timestamp` vào manifest, check `|publish_time - ingest_time|` để phân biệt "CSV cũ" với "pipeline chạy trễ" — phục vụ Distinction (b) và bonus +1 điểm.

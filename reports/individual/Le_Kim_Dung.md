# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Kim Dũng  
**Vai trò:** Cleaning & Quality Owner + Monitoring / Docs Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py` — Rule R7 (strip `[cleaned:...]` tags), R8 (quarantine migration notes), R9 (validate `exported_at` ISO format)
- `quality/expectations.py` — Expectation E7 (`no_migration_notes_in_cleaned`, halt), E8 (`exported_at_within_30d`, warn)
- `data/raw/policy_export_corrupted.csv` — Tạo file dữ liệu corrupted có chủ đích cho Sprint 3 inject
- `docs/data_contract.md`, `docs/pipeline_architecture.md`, `docs/runbook.md`, `docs/quality_report.md` — Hoàn thiện documentation

**Kết nối với thành viên khác:**

Tôi cung cấp file eval (`eval_corrupted.csv`, `eval_clean.csv`, `eval_combined_scenarios.csv`) và log cho thành viên khác trích dẫn trong group report.

**Bằng chứng (commit / comment trong code):**

Các cleaning rules R7/R8/R9 có docstring ghi `metric_impact` trong `cleaning_rules.py`. Artifact nằm trong `artifacts/eval/`, `artifacts/logs/`, `artifacts/manifests/`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)


Tôi thiết kế file `policy_export_corrupted.csv` bằng cách **bỏ migration notes** khỏi chunk "14 ngày" (row 3) và **sửa effective_date** HR cũ "10 ngày" thành `2026-02-01` (row 7). Trong file dirty gốc, cả hai đều bị quarantine bởi R8 và HR stale date — corruption "tự nhiên" bị bắt trước khi cần `--no-refund-fix`. File corrupted mô phỏng tình huống nguy hiểm hơn: dữ liệu bẩn **không có dấu hiệu rõ ràng** nhưng nội dung sai. Khi chạy `--no-refund-fix --skip-validate`, 7 chunk (gồm 2 lỗi) lọt vào vector store, pipeline chuẩn chỉ cho qua 5. E3 và E6 phát hiện 2 violations nhưng bị bypass bởi `--skip-validate`.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Sau pipeline `corrupted`, eval cho thấy `q_refund_window` có `hits_forbidden=yes` — top-1 trả chunk "14 ngày làm việc" thay vì 7 ngày. `q_leave_version` cũng `hits_forbidden=yes` — top-k chứa "10 ngày phép năm" conflict với policy 2026.

**Phát hiện:** Expectation `refund_no_stale_14d_window` FAIL (halt) với `violations=1` trong log `run_corrupted.log`. Eval CSV `eval_corrupted.csv` xác nhận `hits_forbidden=yes` trên 2/4 câu hỏi.

**Fix:** Chạy lại pipeline chuẩn `python etl_pipeline.py run --run-id clean` — prune 6 IDs cũ, upsert 5 chunk sạch. Eval lại: `eval_clean.csv` cho thấy tất cả `hits_forbidden=no`. Delta: `cleaned_records` giảm từ 7 → 5, `quarantine_records` tăng từ 3 → 5.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**File eval gộp:** `artifacts/eval/eval_combined_scenarios.csv` (8 dòng, cột `scenario`)

**Trước (run_id=corrupted):**
```csv
corrupted,q_refund_window,...,contains_expected=yes,hits_forbidden=yes
corrupted,q_leave_version,...,contains_expected=yes,hits_forbidden=yes,top1_doc_expected=yes
```

**Sau (run_id=clean):**
```csv
clean,q_refund_window,...,contains_expected=yes,hits_forbidden=no
clean,q_leave_version,...,contains_expected=yes,hits_forbidden=no,top1_doc_expected=yes
```

**Log chứng minh (trích `run_corrupted.log`):**
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
expectation[hr_leave_no_stale_10d_annual] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed
embed_upsert count=7 collection=day10_kb
```

---

## 5. Cải tiến tiếp theo (40–80 từ)

Tôi sẽ thêm freshness check ở **2 boundary** (ingest + publish): ghi `ingest_timestamp` vào manifest, check `|publish_time - ingest_time|` để phân biệt "CSV cũ" với "pipeline chạy trễ". Đồng thời mở rộng bộ eval từ 4 → 6 câu hỏi, bổ sung slice "refund edge cases" để tăng độ phủ.

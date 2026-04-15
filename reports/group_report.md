# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

**VN:** Nguồn raw dùng file mẫu `data/raw/policy_export_dirty.csv` (10 dòng) mô phỏng export từ hệ nguồn. Pipeline chạy theo chuỗi ingest → clean → expectation validate → embed (Chroma) → ghi manifest → freshness check. `run_id` được in ở stdout và ghi trong `artifacts/logs/run_<run_id>.log`, đồng thời nằm trong `artifacts/manifests/manifest_<run_id>.json`.

**EN:** Raw source is `data/raw/policy_export_dirty.csv` (10 rows). The pipeline executes ingest → cleaning → expectation validation → Chroma embedding → manifest write → freshness check. `run_id` is printed in stdout, logged in `artifacts/logs/run_<run_id>.log`, and stored in `artifacts/manifests/manifest_<run_id>.json`.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

```bash
cd day10/lab
python etl_pipeline.py run --run-id ci-smoke3b
python eval_retrieval.py --out artifacts/eval/before_after_eval_ci-smoke3.csv
python etl_pipeline.py run --run-id inject-bad3 --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad3.csv
python etl_pipeline.py run --run-id ci-smoke3b
```

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `refund_no_stale_14d_window` (halt) | `ci-smoke3b`: OK, `violations=0` | `inject-bad3`: **FAIL**, `violations=1` (nhưng tiếp tục do `--skip-validate`) | Log: `artifacts/logs/run_ci-smoke3b.log`, `artifacts/logs/run_inject-bad3.log` |
| `freshness_check` | `ci-smoke3b`: **FAIL** (data snapshot cũ, vượt SLA 24h) | `inject-bad3`: **FAIL** tương tự | Manifest: `artifacts/manifests/manifest_ci-smoke3b.json`, `manifest_inject-bad3.json` |
| Embed snapshot + prune | `ci-smoke3`: `embed_prune_removed=1`, `embed_upsert count=6` | `inject-bad3`: `embed_upsert count=6` | Log: `artifacts/logs/run_ci-smoke3.log`, `artifacts/logs/run_inject-bad3.log` |

**Rule chính (baseline + mở rộng):**

- **VN:** Pipeline baseline đang có allowlist `doc_id`, chuẩn hoá `effective_date`, quarantine HR policy cũ (trước 2026), loại chunk rỗng, dedupe theo nội dung, và rule fix “refund 14→7 ngày làm việc” (khi bật).  
- **EN:** Baseline includes doc_id allowlist, effective_date normalization, quarantining stale HR policy (<2026), empty-text quarantine, content dedupe, and an optional “refund 14→7 business days” fix.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

**VN:** Run inject `inject-bad3` cố ý tắt fix refund (`--no-refund-fix`) nên expectation `refund_no_stale_14d_window` **FAIL (halt)** với `violations=1`. Để phục vụ “before” retrieval, pipeline vẫn embed nhờ `--skip-validate`. Sau đó chạy lại run chuẩn `ci-smoke3b` (không flag inject) để expectation pass và publish snapshot sạch.  

**EN:** In `inject-bad3`, we disabled the refund fix (`--no-refund-fix`), so `refund_no_stale_14d_window` **FAILED (halt)** with `violations=1`. For “before” evidence we continued embedding via `--skip-validate`, then re-ran the standard pipeline (`ci-smoke3b`) to pass expectations and publish a clean snapshot.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

**VN:** Chạy `inject-bad3` với `--no-refund-fix --skip-validate` để cố ý giữ chunk stale “14 ngày làm việc” trong refund policy và vẫn embed vào Chroma cho mục tiêu so sánh. Sau đó chạy lại pipeline chuẩn (`ci-smoke3b`) để publish snapshot đã clean.  

**EN:** We ran `inject-bad3` with `--no-refund-fix --skip-validate` to intentionally keep the stale “14 business days” refund chunk and still embed it for comparison, then re-ran the standard pipeline (`ci-smoke3b`) to publish a cleaned snapshot.

**Kết quả định lượng (từ CSV / bảng):**

**Evidence files:**
- `artifacts/eval/before_after_eval_ci-smoke3.csv`
- `artifacts/eval/after_inject_bad3.csv`

**Tóm tắt (trích từ CSV):**
- `q_refund_window`: `before_after_eval_ci-smoke3.csv` cho thấy `contains_expected=yes` nhưng `hits_forbidden=yes` (phát hiện dấu vết cụm “14 ngày làm việc” trong top-k). Ở `after_inject_bad3.csv`, `contains_expected=yes` và `hits_forbidden=no`.
- `q_leave_version`: cả hai file đều `contains_expected=yes` và `top1_doc_expected=yes` (top-1 là `hr_leave_policy`).

> Ghi chú: Hai CSV trên phản ánh kết quả retrieval “thực tế” tại thời điểm chạy (top-k=3).

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

**VN:** Với `FRESHNESS_SLA_HOURS=24` (mặc định), freshness check dựa trên `latest_exported_at` trong manifest. Run `ci-smoke3b` ghi `freshness_check=FAIL` vì `latest_exported_at=2026-04-10T08:00:00` (tuổi dữ liệu ~120h > 24h). Đây phù hợp với rubric: dữ liệu mẫu có thể là “snapshot cũ”, nhưng trạng thái FAIL phải được quan sát và ghi rõ trong runbook/monitoring.  

**EN:** With default `FRESHNESS_SLA_HOURS=24`, the freshness check uses `latest_exported_at` in the manifest. `ci-smoke3b` reports `freshness_check=FAIL` because the snapshot is ~120h old (>24h). This is acceptable for sample data as long as it is observable and documented.

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

**VN:** Day 10 embed vào collection `day10_kb` (xem manifest) để tách ranh giới publish cho pipeline dữ liệu. Nếu muốn reuse cho Day 09, có thể cấu hình `CHROMA_DB_PATH`/`CHROMA_COLLECTION` trùng với lab Day 09 hoặc thêm worker retrieval đọc `day10_kb` như một nguồn KB “đã clean”.  

**EN:** Day 10 embeds into `day10_kb` (see manifest) to keep a clean publish boundary for the data pipeline. To reuse in Day 09, we can point Day 09 retrieval to the same `CHROMA_DB_PATH`/`CHROMA_COLLECTION` or treat `day10_kb` as a cleaned KB source.

---

## 6. Rủi ro còn lại & việc chưa làm

- **VN:** `grading_run.py` chưa chạy được vì thiếu `data/grading_questions.json` trong repo tại thời điểm chạy (FileNotFoundError). Khi file được cung cấp, chỉ cần chạy lại `python grading_run.py --out artifacts/eval/grading_run.jsonl`.  
- **EN:** `grading_run.py` could not run because `data/grading_questions.json` was not present at runtime (FileNotFoundError). Once provided, rerun `python grading_run.py --out artifacts/eval/grading_run.jsonl`.

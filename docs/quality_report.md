# Quality report — Lab Day 10 (nhóm 04 — 403)

**run_id (corrupted):** `corrupted`  
**run_id (clean):** `clean`  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Corrupted (`--no-refund-fix --skip-validate`) | Clean (default) | Ghi chú |
|--------|----------------------------------------------|-----------------|---------|
| raw_records | 10 | 10 | Corrupted dùng `policy_export_corrupted.csv` (bỏ migration note, sửa HR date) |
| cleaned_records | **7** | **5** | Corrupted giữ thêm 2 chunk lỗi: stale refund 14d + stale HR 10d |
| quarantine_records | 3 | 5 | Clean quarantine đúng 5 dòng bẩn |
| Expectation halt? | **YES** (2 FAIL: `refund_no_stale_14d_window`, `hr_leave_no_stale_10d_annual`) — bị skip bởi `--skip-validate` | NO (tất cả OK) | Clean pass toàn bộ expectation suite |

---

## 2. Before / after retrieval (bắt buộc)

> File eval gộp: [`artifacts/eval/eval_combined_scenarios.csv`](../artifacts/eval/eval_combined_scenarios.csv)  
> File riêng: [`eval_corrupted.csv`](../artifacts/eval/eval_corrupted.csv) + [`eval_clean.csv`](../artifacts/eval/eval_clean.csv)

### 2.1 Câu hỏi then chốt: refund window (`q_refund_window`)

**Trước (corrupted):**
```
scenario=corrupted | contains_expected=yes | hits_forbidden=YES
top1_preview: "Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn hàng."
```

**Sau (clean):**
```
scenario=clean | contains_expected=yes | hits_forbidden=no
top1_preview: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
```

> **Phân tích:** Khi pipeline chạy `--no-refund-fix`, chunk chứa "14 ngày làm việc" (policy cũ) không được sửa thành "7 ngày".
> Hơn nữa chunk này lọt qua R8 vì file corrupted đã bỏ "ghi chú: bản sync cũ — lỗi migration".
> Kết quả: retrieval trả về chunk stale ở **top-1**, `hits_forbidden=yes` — LLM sẽ trả lời sai với thông tin hết hạn.

### 2.2 Merit (versioning HR): `q_leave_version`

**Trước (corrupted):**
```
scenario=corrupted | contains_expected=yes | hits_forbidden=YES | top1_doc_expected=yes
top1_preview: "Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026."
```

**Sau (clean):**
```
scenario=clean | contains_expected=yes | hits_forbidden=no | top1_doc_expected=yes
top1_preview: "Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026."
```

> **Phân tích:** Top-1 đều trả đúng doc `hr_leave_policy` với chunk 12 ngày (2026).
> Tuy nhiên khi corrupted, chunk "10 ngày phép năm" (HR cũ — đã bị sửa effective_date thành 2026 trong file corrupted) vẫn tồn tại trong top-k → `hits_forbidden=yes`.
> Điều này nghĩa là LLM có thể bị nhiễu bởi context trái ngược nhau trong top-k.

### 2.3 So sánh tổng hợp (từ `eval_combined_scenarios.csv`)

| scenario | question_id | contains_expected | hits_forbidden | top1_doc_expected |
|----------|------------|-------------------|----------------|-------------------|
| corrupted | q_refund_window | yes | **yes** ❌ | — |
| corrupted | q_p1_sla | yes | no | — |
| corrupted | q_lockout | yes | no | — |
| corrupted | q_leave_version | yes | **yes** ❌ | yes |
| clean | q_refund_window | yes | no ✅ | — |
| clean | q_p1_sla | yes | no ✅ | — |
| clean | q_lockout | yes | no ✅ | — |
| clean | q_leave_version | yes | no ✅ | yes |

---

## 3. Freshness & monitor

**Kết quả `freshness_check`:** `FAIL`

```
freshness_check=FAIL {
  "latest_exported_at": "2026-04-10T08:00:00",
  "age_hours": 122.43,
  "sla_hours": 24.0,
  "reason": "freshness_sla_exceeded"
}
```

**Giải thích:** SLA freshness được cấu hình `FRESHNESS_SLA_HOURS=24` (mặc định — xem `.env`).
Dữ liệu raw CSV có `exported_at = 2026-04-10T08:00:00` (cách thời điểm chạy ~122 giờ) → vượt SLA 24h.
Trong production, alert này sẽ trigger re-export từ DB nguồn để KB luôn cập nhật.

---

## 4. Corruption inject (Sprint 3)

### 4.1 Phương pháp inject

Tạo file **`data/raw/policy_export_corrupted.csv`** — biến thể có chủ đích từ `policy_export_dirty.csv`:

| # | Loại corruption | Gốc (dirty) | Corrupted | Mục đích |
|---|-----------------|-------------|-----------|----------|
| 1 | **Stale refund window** | Chunk 3 chứa "14 ngày" + "bản sync cũ — lỗi migration" → bị R8 quarantine | **Bỏ migration note** → chunk "14 ngày" lọt qua cleaning | Chứng minh nếu thiếu R8, chunk stale policy lọt vào KB |
| 2 | **Stale HR version** | Chunk 7 có `effective_date=2025-01-01` → bị quarantine (stale HR date) | **Sửa effective_date thành 2026-02-01** → lọt qua date check, nhưng nội dung vẫn chứa "10 ngày phép năm" (HR cũ) | Chứng minh date-based filter không đủ — cần expectation content-level |
| 3 | **Duplicate** | Chunk 1 & 2 trùng text → dedup giữ 1 | Giữ nguyên — dedup vẫn hoạt động | Baseline: duplicate vẫn bị bắt |

### 4.2 Lệnh chạy inject

```bash
python etl_pipeline.py run \
  --raw data/raw/policy_export_corrupted.csv \
  --run-id corrupted \
  --no-refund-fix \
  --skip-validate
```

- `--no-refund-fix`: tắt rule sửa "14 ngày → 7 ngày" trong `policy_refund_v4`
- `--skip-validate`: khi expectation suite FAIL (halt), vẫn tiếp tục embed → dữ liệu bẩn vào Chroma

### 4.3 Log chứng minh (trích `artifacts/logs/run_corrupted.log`)

```
run_id=corrupted
raw_records=10
cleaned_records=7                    ← nhiều hơn clean (5) vì 2 chunk lỗi lọt qua
quarantine_records=3
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1     ← Expectation bắt đúng!
expectation[hr_leave_no_stale_10d_annual] FAIL (halt) :: violations=1   ← Expectation bắt đúng!
WARN: expectation failed but --skip-validate -> tiep tuc embed (chi dung cho demo Sprint 3).
embed_upsert count=7 collection=day10_kb    ← 7 chunk (gồm 2 lỗi) vào vector store
```

### 4.4 Impact đo được

| Câu hỏi | Metric bị ảnh hưởng | Corrupted | Clean |
|----------|---------------------|-----------|-------|
| `q_refund_window` | `hits_forbidden` (faithfulness proxy) | **yes** — top-1 trả chunk "14 ngày" hết hạn | no |
| `q_leave_version` | `hits_forbidden` (answer_relevance proxy) | **yes** — top-k chứa chunk "10 ngày" conflict | no |

> **Kết luận:** Expectation suite (E3, E6) phát hiện chính xác dữ liệu bẩn. Khi `--skip-validate` bypass halt, dữ liệu lỗi embed vào KB → eval retrieval xuống cấp rõ rệt. Pipeline **bắt buộc** phải giữ halt gate trong production.

---

## 5. Hạn chế & việc chưa làm

- **Freshness luôn FAIL** trong demo vì `exported_at` trong CSV mẫu là ngày cũ (`2026-04-10`). Trong production cần tích hợp trigger export real-time hoặc cron job cập nhật CSV.
- **Chưa có test tự động cho R7/R8/R9** — hiện chỉ qua pipeline log. Nên bổ sung unit test cho cleaning rules.
- **Embedding model nhỏ** (`all-MiniLM-L6-v2`) — chunk ngắn bằng tiếng Việt có thể bị rank sai khi corpus lớn hơn. Cân nhắc multilingual model.
- **Eval chỉ dùng keyword matching**, chưa áp dụng LLM-as-Judge (Faithfulness / Completeness) cho retrieval. Cần tích hợp SCORING.md pipeline.
- **Chưa tự động hoá** quy trình corruption inject → eval → report. Có thể viết shell script CI chạy 2 scenario và so diff.

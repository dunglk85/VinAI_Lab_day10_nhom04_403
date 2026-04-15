# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Ngô Gia Bảo
**Vai trò:** Ingestion / Cleaning / Embed / Monitoring — Ingestion / Cleaning / Embed / Monitoring  
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- Tôi phụ trách chạy end-to-end pipeline và thu thập bằng chứng quan sát được (observability) cho nhóm: chạy kịch bản “chuẩn” và “inject-bad”, xuất các artifact cleaned/quarantine/manifest và chạy eval retrieval để có before/after.  

**Các file tôi trực tiếp sử dụng/đối chiếu (read/execute):**
- `etl_pipeline.py` (entrypoint run + manifest + freshness)
- `eval_retrieval.py` (golden retrieval checks, top-k=3)
- Artifacts: `artifacts/manifests/manifest_ci-smoke3b.json`, `artifacts/eval/before_after_eval_ci-smoke3.csv`, `artifacts/eval/after_inject_bad3.csv`

**Kết nối với thành viên khác:**
 Tôi cung cấp cho “Cleaning/Quality owner” các run_id và log line expectation PASS/FAIL để họ điền bảng `metric_impact` trong báo cáo nhóm; đồng thời cung cấp 2 file CSV eval để “Docs/Monitoring owner” trích dẫn phần before/after và freshness.  


**Bằng chứng (commit / comment trong code):**

Bằng chứng ở artifact + log được tạo bởi các lệnh chạy thật (xem mục 4). Nếu lớp yêu cầu trace qua commit: tôi sẽ commit các file trong `artifacts/eval/` và `artifacts/manifests/` đúng theo deadline của `SCORING.md`.  


---

## 2. Một quyết định kỹ thuật (100–150 từ)

> VD: chọn halt vs warn, chiến lược idempotency, cách đo freshness, format quarantine.

Tôi chọn cách tạo bằng chứng “before” một cách có kiểm soát: chạy `inject-bad3` với `--no-refund-fix --skip-validate` để cố ý cho expectation `refund_no_stale_14d_window` FAIL (halt) nhưng vẫn embed vào Chroma nhằm đo tác động lên retrieval. Sau đó tôi chạy lại pipeline chuẩn `ci-smoke3b` để publish snapshot sạch và tránh vector stale tồn tại lâu. Quyết định này bám đúng mục tiêu observability: nhìn được “pipeline sẽ HALT nếu validate bật”, nhưng vẫn có khả năng tạo dữ liệu xấu cho thí nghiệm Sprint 3, rồi quay lại trạng thái sạch cho grading/delivery.  


---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

> Mô tả triệu chứng → metric/check nào phát hiện → fix.

 Anomaly tôi ghi nhận là freshness luôn báo FAIL ngay cả khi pipeline “OK”. Ở run chuẩn `ci-smoke3b`, log ghi `freshness_check=FAIL` với `latest_exported_at="2026-04-10T08:00:00"` và `age_hours≈120` so với `sla_hours=24`. Tôi không “fix” bằng cách chỉnh bừa SLA để PASS, mà giữ nguyên trạng thái FAIL vì dữ liệu mẫu là snapshot cũ (đúng FAQ trong `SCORING.md`). Tôi ghi rõ ý nghĩa FAIL trong báo cáo nhóm (freshness là signal cho data recency, không phải lỗi ETL), và đề xuất nếu sản phẩm thật thì SLA/định nghĩa freshness phải gắn với boundary ingest/publish và timestamp nguồn.  
---

## 4. Bằng chứng trước / sau (80–120 từ)

> Dán ngắn 2 dòng từ `before_after_eval.csv` hoặc tương đương; ghi rõ `run_id`.

Evidence before/after nằm ở 2 file CSV:
- `artifacts/eval/before_after_eval_ci-smoke3.csv` (sau run “chuẩn” `ci-smoke3`) có dòng `q_refund_window` với `contains_expected=yes` nhưng `hits_forbidden=yes` (top-k vẫn còn dấu vết “14 ngày làm việc”).  
- `artifacts/eval/after_inject_bad3.csv` (sau run inject `inject-bad3`) có `q_refund_window` với `contains_expected=yes` và `hits_forbidden=no`.  
Ngoài ra, `q_leave_version` cho thấy `top1_doc_expected=yes` và top-1 doc là `hr_leave_policy` (ổn định qua các run).
---

## 5. Cải tiến tiếp theo (40–80 từ)

> Nếu có thêm 2 giờ — một việc cụ thể (không chung chung).

 Tôi sẽ bổ sung 1–2 câu hỏi retrieval mới (≥5 tổng) để tăng độ phủ của eval, đặc biệt là slice “refund edge cases” và “HR version boundary”. Đồng thời, tôi sẽ thêm một check “freshness at publish boundary” (run_timestamp vs exported_at) để phân biệt data snapshot cũ với pipeline chạy trễ.  

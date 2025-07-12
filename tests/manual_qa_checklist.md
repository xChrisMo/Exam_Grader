# Manual QA Checklist for Exam Grader

## 1. Submission Workflow
- [ ] Upload a valid PDF/image submission and confirm success toast/modal
- [ ] Upload an unsupported file type and confirm error feedback
- [ ] Upload a large file and confirm error/limit feedback
- [ ] Confirm real-time progress updates (WebSocket or AJAX fallback)
- [ ] Simulate network loss during upload and confirm error/retry UI

## 2. OCR & Grading
- [ ] Confirm OCR progress and status updates in real time
- [ ] Simulate OCR failure (corrupt file) and confirm error feedback and retry option
- [ ] Confirm LLM grading progress and status updates
- [ ] Simulate LLM API failure and confirm error feedback and retry option

## 3. Results & Reports
- [ ] View results page and confirm all scores, grades, and feedback are visible
- [ ] Download PDF report and confirm content/format
- [ ] Download JSON report and confirm content/format
- [ ] Attempt to download report for another user’s submission and confirm access denied

## 4. Dashboard & Progress
- [ ] Confirm dashboard updates in real time for new/graded submissions
- [ ] Confirm progress bars and status indicators update correctly
- [ ] Simulate job failure and confirm error/retry UI

## 5. Accessibility & Responsiveness
- [ ] Navigate all pages using keyboard only (Tab, Enter, Space)
- [ ] Confirm ARIA roles and live regions are present on progress/status elements
- [ ] Test color contrast and font size on all major UI elements
- [ ] Test on mobile device and confirm responsive layout

## 6. Security & Rate Limiting
- [ ] Attempt to access endpoints without login and confirm redirect/denied
- [ ] Exceed rate limits and confirm error feedback
- [ ] Attempt CSRF attack and confirm protection

## 7. Health & Monitoring
- [ ] Call /api/health and confirm all components are healthy
- [ ] Simulate Celery/DB down and confirm health endpoint reports error

---

**Record all issues found and steps to reproduce. Attach screenshots for UI/UX bugs.**
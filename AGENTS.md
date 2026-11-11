# CAD workflow project

For drawing, dimensioning, print export, or missing-line investigation, read `docs/agent-workflow.md` first. For failures, also read `docs/troubleshooting.md`.

Keep geometry values and display scale separate. Treat input drawings as read-only. Run `pytest -q` after code changes. Export and visually inspect the synthetic demo after renderer changes. Unsupported entities must produce actionable errors, not successful but incomplete PDFs. Keep private drawings, credentials, absolute personal paths and generated outputs out of commits.

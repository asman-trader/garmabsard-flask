import os
import sys
import time
import uuid

# Ensure project root on sys.path
ROOT = os.path.abspath(os.getcwd())
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from admin.sms_campaign import _run_sms_job, _create_job, _load_jobs


def main():
    app = create_app()
    job_id = str(uuid.uuid4())

    # Test numbers and parameters
    numbers = [
        "+989121111111",
        "09121234567",
    ]
    template_id = 335146
    params = {"code": "12345"}
    mode = "fixed"
    delay_ms = 10
    dry_run = True  # set to False to try real API send

    # Create job record
    _create_job(job_id, total=len(numbers), template_id=template_id,
                mode=mode, delay_ms=delay_ms, min_ms=None, max_ms=None)

    # Run worker synchronously (direct call) with app context
    _run_sms_job(app, job_id, numbers, template_id, params, mode, delay_ms, None, None, dry_run)

    # Read job results
    data = _load_jobs()
    job = data.get("jobs", {}).get(job_id)
    print("JOB:", job_id)
    print(job)


if __name__ == "__main__":
    main()



"""
Celery tasks for the assignment application
"""

# Django
from django.conf import settings

# Standard Library
import csv
import logging
from datetime import date
from hashlib import md5
from time import time
from urllib.parse import quote_plus

# Third Party
import requests
from smart_open import open as smart_open

# SpotUs
from config import celery_app
from spotus.assignments.models import Assignment
from spotus.core.email import TemplateEmail
from spotus.users.models import User

logger = logging.getLogger(__name__)


@celery_app.task()
def datum_per_page(assignment_pk, doc_id, metadata, **kwargs):
    """Create an assignment data item for each page of the document"""

    assignment = Assignment.objects.get(pk=assignment_pk)

    doc_id = quote_plus(doc_id.encode("utf-8"))
    resp = requests.get(f"https://www.documentcloud.org/api/documents/{doc_id}.json")
    try:
        resp.raise_for_status()
        resp_json = resp.json()
    except (ValueError, requests.exceptions.HTTPError) as exc:
        datum_per_page.retry(
            args=[assignment_pk, doc_id, metadata],
            countdown=300,
            kwargs=kwargs,
            exc=exc,
        )
    pages = resp_json["document"]["pages"]
    for i in range(1, pages + 1):
        assignment.data.create(
            url=f"https://www.documentcloud.org/documents/{doc_id}/pages/{i}.html",
            metadata=metadata,
        )


@celery_app.task()
def import_doccloud_proj(
    assignment_pk, proj_id, metadata, doccloud_each_page, **kwargs
):
    """Import documents from a document cloud project"""

    assignment = Assignment.objects.get(pk=assignment_pk)
    json_url = f"https://www.documentcloud.org/api/projects/{proj_id}.json"

    resp = requests.get(
        json_url,
        auth=(settings.DOCUMENTCLOUD_USERNAME, settings.DOCUMENTCLOUD_PASSWORD),
    )
    try:
        resp_json = resp.json()
    except ValueError as exc:
        import_doccloud_proj.retry(
            args=[assignment_pk, proj_id, metadata],
            countdown=300,
            kwargs=kwargs,
            exc=exc,
        )
    else:
        if "error" in resp_json:
            logger.warn("Error importing DocCloud project: %s", proj_id)
            return
        for doc_id in resp_json["project"]["document_ids"]:
            if doccloud_each_page:
                datum_per_page.delay(assignment.pk, doc_id, metadata)
            else:
                assignment.data.create(
                    url=f"https://www.documentcloud.org/documents/{doc_id}.html",
                    metadata=metadata,
                )


class AsyncFileDownloadTask:
    """Base behavior for asynchrnously generating large files for downloading

    Subclasses should set:
    self.dir_name - directory where files will be stored on s3
    self.file_name - name of the file
    self.html_template - html template for notification email
    self.subject - subject line for notification email
    """

    def __init__(self, user_pk, hash_key):
        self.user = User.objects.get(pk=user_pk)
        today = date.today()
        md5sum = md5(
            f"{int(time())}{settings.SECRET_KEY}{user_pk}{hash_key}".encode("ascii")
        ).hexdigest()
        self.file_path = (
            f"{self.dir_name}/{today.year:4d}/{today.month:02d}/"
            f"{today.day:02d}/{md5sum}/{self.file_name}"
        )

    def get_context(self):
        """Get context for the notification email"""
        return {"file": self.file_path}

    def send_notification(self):
        """Send the user the link to their file"""
        notification = TemplateEmail(
            user=self.user,
            extra_context=self.get_context(),
            html_template=self.html_template,
            subject=self.subject,
        )
        notification.send(fail_silently=False)

    def run(self):
        """Task entry point"""
        with smart_open(
            f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{self.file_path}",
            "wb",
            transport_params={"multipart_upload_kwargs": {"ACL": "public-read"}},
        ) as out_file:
            self.generate_file(out_file)

        self.send_notification()

    def generate_file(self, out_file):
        """Abstract method"""
        raise NotImplementedError("Subclass must override generate_file")


class ExportCsv(AsyncFileDownloadTask):
    """Export the results of the assignment for the user"""

    dir_name = "exported_csv"
    file_name = "results.csv"
    html_template = "message/notification/csv_export.html"
    subject = "Your CSV Export"

    def __init__(self, user_pk, assignment_pk):
        super().__init__(user_pk, assignment_pk)
        self.assignment = Assignment.objects.get(pk=assignment_pk)

    def generate_file(self, out_file):
        """Export all responses as a CSV file"""
        metadata_keys = self.assignment.get_metadata_keys()
        include_emails = self.user.is_staff

        writer = csv.writer(out_file)
        writer.writerow(
            self.assignment.get_header_values(metadata_keys, include_emails)
        )
        for csr in self.assignment.responses.all().iterator():
            writer.writerow(csr.get_values(metadata_keys, include_emails))


@celery_app.task()
def export_csv(assignment_pk, user_pk):
    """Export the results of the assignment for the user"""
    ExportCsv(user_pk, assignment_pk).run()

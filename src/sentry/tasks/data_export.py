from __future__ import absolute_import

import csv
import tempfile

from django.db import transaction
from django.core.files.storage import default_storage

from sentry import tagstore
from sentry.constants import ExportQueryType
from sentry.models import EventUser, File, Group, Project, get_group_with_redirect
from sentry.tasks.base import instrumented_task

SNUBA_MAX_RESULTS = 1000

tmp_dir = tempfile.mkdtemp()


@instrumented_task(name="sentry.tasks.data_export.compile_data", queue="data_export")
def compile_data(data_export):
    # Create a temporary file
    with tempfile.TemporaryFile() as tf:
        # Process the query based on its type
        if data_export.query_type == ExportQueryType.DISCOVER_V2:
            process_discover_v2(data_export, tf)
            return
        elif data_export.query_type == ExportQueryType.BILLING_REPORT:
            process_billing_report(data_export, tf)
            return
        elif data_export.query_type == ExportQueryType.ISSUE_BY_TAG:
            file_name = process_issue_by_tag(data_export, tf)
        # Create a new File object and attach it to the ExportedData
        tf.seek(0)
        with transaction.atomic():
            file = File.objects.create(name=file_name, type="export.csv")
            file.putfile(tf)
            data_export.update(file=file)
    test_download(data_export, file_name)


def process_discover_v2(data_export, file):
    # TODO(Leander): Implement processing for Discover V2
    return


def process_billing_report(data_export, file):
    # TODO(Leander): Implement processing for Billing Reports
    return


def process_issue_by_tag(data_export, file):
    """
    Convert tag payload to a CSV, returns (file_path, file_name) as a tuple
    (Adapted from 'src/sentry/web/frontend/group_tag_export.py')
    """
    # Get the pertaining project
    payload = data_export.query_info
    project = Project.objects.get(slug=payload["project_slug"])

    # Get the pertaining issue
    group, _ = get_group_with_redirect(
        payload["group_id"], queryset=Group.objects.filter(project=project)
    )

    # Get the pertaining key
    key = payload["key"]
    lookup_key = u"sentry:{0}".format(key) if tagstore.is_reserved_key(key) else key

    # If the key is the 'user' tag, attach the event user
    def attach_eventuser(items):
        users = EventUser.for_tags(group.project_id, [i.value for i in items])
        for item in items:
            item._eventuser = users.get(item.value)

    # Create the fields/callback lists
    if key == "user":
        callbacks = [attach_eventuser]
        fields = [
            "value",
            "id",
            "email",
            "username",
            "ip_address",
            "times_seen",
            "last_seen",
            "first_seen",
        ]
    else:
        callbacks = []
        fields = ["value", "times_seen", "last_seen", "first_seen"]

    # Example file name: ISSUE_BY_TAG-project10-user__721.csv
    file_details = u"{}-{}__{}".format(payload["project_slug"], key, data_export.id)
    file_name = get_file_name(ExportQueryType.ISSUE_BY_TAG_STR, file_details)

    # Iterate through all the GroupTagValues
    writer = csv.DictWriter(file, fields)
    writer.writeheader()
    iteration = 0
    while True:
        gtv_list = tagstore.get_group_tag_value_iter(
            project_id=group.project_id,
            group_id=group.id,
            environment_id=None,
            key=lookup_key,
            callbacks=callbacks,
            offset=SNUBA_MAX_RESULTS * iteration,
        )
        gtv_list_raw = [serialize_issue_by_tag(key, item) for item in gtv_list]
        if len(gtv_list_raw) == 0:
            break
        writer.writerows(gtv_list_raw)
        iteration += 1
    return file_name


def get_file_name(type, custom_string, extension="csv"):
    file_name = u"{}-{}.{}".format(type, custom_string, extension)
    return file_name


def test_download(data_export, file_name):
    file = data_export.file
    raw_file = file.getfile()
    default_storage.save("/tmp/sentry-media/testing/" + file_name, raw_file)


def alert_error():
    # TODO(Leander): Handle errors in these tasks.
    return


################################
#  Process-specific functions  #
################################


def serialize_issue_by_tag(key, item):
    result = {
        "value": item.value,
        "times_seen": item.times_seen,
        "last_seen": item.last_seen.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "first_seen": item.first_seen.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }
    if key == "user":
        euser = item._eventuser
        result["id"] = euser.ident if euser else ""
        result["email"] = euser.email if euser else ""
        result["username"] = euser.username if euser else ""
        result["ip_address"] = euser.ip_address if euser else ""
    return result

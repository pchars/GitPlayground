from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render

from .importer import TaskImportError, import_task_zip, inspect_task_zip


class TaskZipUploadForm(forms.Form):
    archive = forms.FileField(help_text="ZIP with task manifest and assets")


@staff_member_required
def upload_task_zip_view(request):
    form = TaskZipUploadForm(request.POST or None, request.FILES or None)
    context = {"form": form, "title": "Upload task ZIP"}
    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action", "preview")
        uploaded = form.cleaned_data["archive"].read()
        try:
            if action == "preview":
                context["preview"] = inspect_task_zip(uploaded)
                context["is_dry_run"] = True
            else:
                result = import_task_zip(uploaded)
                messages.success(
                    request,
                    f"Task {result.task.external_id} imported with {result.imported_assets} assets.",
                )
                return redirect("/admin/tasks/task/")
        except TaskImportError as exc:
            form.add_error("archive", str(exc))
    return render(request, "admin/tasks/upload_task.html", context)

from drive.utils.files import FileManager
from frappe.core.doctype.file.file import File as FrappeFile
from frappe.utils import get_files_path
import frappe
from pathlib import Path
from drive.utils import get_upload_path


def only_for_drive_files(func):
    def inner(self, *args, **kwargs):
        if self.is_drive_file:
            return func(self, *args, **kwargs)
        else:
            parent_func = getattr(super(type(self), self), func.__name__, None)
            if not parent_funcfunc:
                raise ValueError("This function only exists for Drive files.")
            return parent_func(*args, **kwargs)

    return inner


class File(FrappeFile):
    @only_for_drive_files
    def validate(self):
        pass

    # @only_for_drive_files
    # def before_insert(self):
    #     pass

    @only_for_drive_files
    def generate_content_hash(self):
        pass

    @only_for_drive_files
    def get_full_path(self):
        return get_files_path(self.file_url, private=True)

    @only_for_drive_files
    def set_folder_name(self):
        pass

    @only_for_drive_files
    def autoname(self):
        if getattr(self, "_name", None):
            self.name = self._name
        else:
            self.name = frappe.generate_hash(length=10)

    @only_for_drive_files
    def set_is_private(self):
        self.is_private = 1

    @only_for_drive_files
    def set_file_type(self):
        pass


def after_upload_file(doc):
    settings = frappe.get_single("Drive Disk Settings")
    if frappe.form_dict.library_file_name:
        library_doc = frappe.get_doc("File", frappe.form_dict.library_file_name)
        doc.is_drive_file = library_doc.is_drive_file
        if doc.is_drive_file:
            doc.file_type = library_doc.file_type
            doc.file_size = library_doc.file_size
            doc.special_file = "File"
            doc.special_file_doc = frappe.form_dict.library_file_name
    elif settings.use_drive_for_files:
        doc.is_drive_file = 1

        # print('Using Drive!')
        # raise Exception('Using Drive!')
    return doc


def write_file(doc):
    if not doc.is_drive_file:
        return self.save_file_on_filesystem()

    if doc.attached_to_name:
        temp_path = get_upload_path("", doc.content_hash[:6] + "-" + doc.file_name)
        with temp_path.open("wb") as f:
            f.write(doc.content)

        file_path = Path(doc.attached_to_doctype) / doc.attached_to_name / doc.file_name
        save_folder = Path(frappe.get_site_path()) / "private/files" / file_path.parent
        if not save_folder.exists():
            save_folder.mkdir(parents=True)

        doc.file_url = str(file_path)
        manager = FileManager()
        manager.upload_file(temp_path, doc)
        return {"file_url": str(file_path), "file_name": doc.file_name}

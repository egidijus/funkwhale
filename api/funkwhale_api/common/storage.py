import os
import shutil
import slugify

from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


def asciionly(name):
    """
    Convert unicode characters in name to ASCII characters.
    """
    return slugify.slugify(name, ok=slugify.SLUG_OK + ".", only_ascii=True)


class ASCIIFileSystemStorage(FileSystemStorage):
    def get_valid_name(self, name):
        return super().get_valid_name(asciionly(name))

    def force_delete(self, name):
        path = self.path(name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                return super().delete(name)
        except FileNotFoundError:
            pass


class ASCIIS3Boto3Storage(S3Boto3Storage):
    def get_valid_name(self, name):
        return super().get_valid_name(asciionly(name))

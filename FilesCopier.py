import datetime
import os
import shutil
from enum import Enum
from typing import Optional, Callable

from PIL import Image


class InformationType(Enum):
    IS_DIRECTORY = 1
    IMAGE_WITHOUT_CREATION_DATE = 2
    IMAGE_ERROR = 4
    DESTINATION_ALREADY_EXISTS = 5
    MOVING_ERROR = 6
    PANORAMIC_IMAGE = 7


class FilesCopier:

    def __init__(self, move_files: bool = False, rename_to_creation_date: bool = False,
                 resize_images: bool = False, resize_bigger_length: int = 4000,
                 resize_jpeg_compression: int = 95, debug: bool = False, on_output_info: Callable = None):
        self.move_files = move_files
        self.rename_to_creation_date = rename_to_creation_date
        self.resize_images = resize_images
        self.resize_bigger_length = resize_bigger_length
        self.resize_jpeg_compression = resize_jpeg_compression
        self.debug = debug
        self.on_output_info = on_output_info

    def iterate_dir(self, src_dir_path: str, dest_dir_path: str, on_progress_updated: Callable = None):
        self.debug_print('copy_and_rename_dir_images')
        src_file_list = os.listdir(src_dir_path)
        src_file_count = len(src_file_list)
        for i in range(0, src_file_count):
            if on_progress_updated:
                on_progress_updated(i + 1, src_file_count)
            self.copy_file(src_dir_path, dest_dir_path, src_file_list[i])

    def copy_file(self, src_dir_path: str, dest_dir_path: str, src_file_name: str):
        same_dirs = src_dir_path == dest_dir_path
        src_file_path = os.path.join(src_dir_path, src_file_name)
        if os.path.isdir(src_file_path):
            self.output_info(InformationType.IS_DIRECTORY, src_file_name)
            return
        if not self.rename_to_creation_date and not self.resize_images:
            self.only_copy_or_move(same_dirs, src_file_path, dest_dir_path)
        else:
            try:
                dest_file_name = src_file_name
                src_img: Image = Image.open(src_file_path, mode='r')

                if self.rename_to_creation_date:
                    creation_date = self.get_image_creation_date(src_img)
                    if creation_date is not None:
                        dest_file_name = self.get_free_filename(os.path.join(dest_dir_path, creation_date +
                                                                             os.path.splitext(src_file_name)[1]))
                    else:
                        self.output_info(InformationType.IMAGE_WITHOUT_CREATION_DATE, src_file_name)

                if self.resize_images:
                    self.resize_image(src_img, os.path.join(dest_dir_path, dest_file_name), src_file_name)
                    if same_dirs and src_file_name != dest_file_name or self.move_files and not same_dirs:
                        os.remove(src_file_path)
                elif same_dirs:
                    if src_file_name != dest_file_name:
                        self.move_file(src_file_path, dest_dir_path, dest_file_name)
                elif self.move_files:
                    self.move_file(src_file_path, dest_dir_path, dest_file_name)
                elif not self.move_files:
                    shutil.copy2(src_file_path, dest_dir_path)
            except IOError as e:
                if str(e).startswith('cannot identify image file'):
                    pass
                else:
                    self.output_info(InformationType.IMAGE_ERROR, src_file_name, str(e))
                self.only_copy_or_move(same_dirs, src_file_path, dest_dir_path)

    def only_copy_or_move(self, same_dirs: bool, src_file_path: str, dest_dir_path: str):
        if same_dirs:
            pass
        elif self.move_files:
            self.move_file(src_file_path, dest_dir_path)
        else:
            shutil.copy2(src_file_path, dest_dir_path)

    @staticmethod
    def get_image_creation_date(src_img: Image) -> Optional[str]:
        try:
            # noinspection PyProtectedMember
            exif_tags = src_img._getexif()
            if exif_tags is not None:
                # get EXIF tag DATE_TIME_ORIGINAL
                creation_date = datetime.datetime.strptime(exif_tags[36867], '%Y:%m:%d %H:%M:%S')
                return creation_date.strftime('%Y_%m_%d_%H_%M_%S')
        except KeyError:
            return None

    def resize_image(self, src_img: Image, dest_file_path: str, src_file_name: str):
        ext = os.path.splitext(dest_file_path)[1][1:].lower()
        if ext == 'jpg':
            ext = 'jpeg'
        ratio = self.resize_bigger_length / max(src_img.size)
        if max(src_img.size) / min(src_img.size) >= 2.4:
            self.output_info(InformationType.PANORAMIC_IMAGE, src_file_name)
            img_resized = src_img
        elif ratio > 1.0:
            img_resized = src_img
        else:
            new_size = tuple(int(ratio * x) for x in src_img.size)
            img_resized: Image = src_img.resize(new_size, resample=Image.LANCZOS)
        try:
            img_resized.save(dest_file_path, ext, quality=self.resize_jpeg_compression,
                             exif=src_img.info['exif'])
        except KeyError:
            img_resized.save(dest_file_path, ext, quality=self.resize_jpeg_compression)

    @staticmethod
    def get_free_filename(filepath: str) -> str:
        (root, ext) = os.path.splitext(filepath)
        i = 2
        while os.path.exists(filepath):
            filepath = '%s_%d%s' % (root, i, ext)
            i = i + 1
        return os.path.split(filepath)[1]

    def move_file(self, src_file_path: str, dest_dir_path: str, dest_file_name: str = None):
        if dest_file_name is None:
            dest_file_name = os.path.split(src_file_path)[1]
        try:
            shutil.move(src_file_path, os.path.join(dest_dir_path, dest_file_name))
        except shutil.Error as e:
            if str(e) == 'Destination path \'%s\' already exists' % \
                    os.path.join(dest_dir_path, os.path.split(src_file_path)[1]):
                self.output_info(InformationType.DESTINATION_ALREADY_EXISTS, os.path.split(src_file_path)[1])
            else:
                self.output_info(InformationType.MOVING_ERROR, os.path.split(src_file_path)[1], str(e))

    def debug_print(self, *argv):
        if self.debug:
            print(*argv)

    def output_info(self, info_type: InformationType, filename: str, text: str = ''):
        if self.on_output_info:
            self.on_output_info(info_type, filename, text)

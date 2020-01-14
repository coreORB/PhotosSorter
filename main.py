import datetime
import os
import queue
import shutil
import threading
from typing import List
from unittest.test.testmock.testpatch import function

import PySimpleGUI as sG
from PIL import Image

debug = False

gui_text_src_dir = 'Foldery źródłowe:'
gui_text_add = 'Dodaj'
gui_text_delete = 'Usuń'
gui_text_dest_dir = 'Folder docelowy:'
gui_text_browse = 'Przeglądaj...'
gui_text_copy_mode = 'Tryb zapisu'
gui_text_only_copy = 'tylko kopiuj'
gui_text_resize = 'kopiuj ze zmianą rozmiaru'
gui_text_resize_bigger_size = 'Rozmiar dłuższego boku (w px)'
gui_text_resize_jpeg_compression = 'Stopień kompresji JPEG (1-95)'
gui_text_start = 'START'
gui_text_progress = 'Plik: %d/%d'
gui_text_done = 'Zakończone'
gui_text_progress_current_dir = 'Katalog: %s'
gui_text_progress_warn_is_directory = '   "%s" pominięty - jest katalogiem'
gui_text_progress_warn_not_compatible_image = '   "%s" pominięty - nie jest wspieranym plikiem graficznym'
gui_text_progress_warn_no_timestamp = '   "%s" pominięty - nie zawiera informacji o dacie wykonania'
gui_text_validation_title = 'Błąd walidacji'
gui_text_validation_in_dir_no_dirs = 'Podaj folder(y) źródłowy'
gui_text_validation_in_dir = 'Folder źródłowy "%s" nie istnieje lub nie jest katalogiem'
gui_text_validation_out_dir_no_dir = 'Podaj folder docelowy'
gui_text_validation_out_dir = 'Folder docelowy nie istnieje lub nie jest katalogiem'
gui_text_validation_out_dir_in_in_dirs = 'Folder docelowy jest taki sam jak jeden z folderów źródłowych'
gui_text_validation_jpeg_compression = 'Stopień kompresji JPEG musi być liczbą całkowitą w przedziale 1-95'
gui_text_validation_bigger_size = 'Rozmiar dłuższego boku musi być liczbą całkowitą'

dft_in_dirs = []
dft_out_dir = 'C:\\Users\\ZaYeR\\Desktop\\temp'
dft_resize_bigger_size = 2000
dft_jpeg_compression = 95
dft_skip_images_without_creation_date = False


def main():
    show_main_window()


def show_main_window():
    in_dirs = dft_in_dirs
    gui_queue = queue.Queue()
    # All the stuff inside your window.
    layout = [
        [sG.Frame(gui_text_src_dir, [
            [sG.Listbox(dft_in_dirs, key='lb_in_dirs', enable_events=True, size=[100, 10])],
            [sG.FolderBrowse(gui_text_add, key='b_in_dir', enable_events=True, target='b_in_dir'),
             sG.Button(gui_text_delete, key='b_in_dir_delete')]
        ], element_justification='right', key='f_in_dirs')],
        [sG.Frame(gui_text_dest_dir, [
            [sG.InputText(key='it_out_dir', default_text=dft_out_dir, size=[102, 1])],
            [sG.FolderBrowse(gui_text_browse, key='b_out_dir', target='it_out_dir')]
        ], element_justification='right', key='f_out_dir')],
        [sG.Frame(gui_text_copy_mode, [
            [sG.Radio(gui_text_only_copy, 'resize_or_copy', default=True, key='r_only_copy')],
            [sG.Radio(gui_text_resize, 'resize_or_copy', default=False, key='r_resize')],
            [sG.Text('    '), sG.Text(gui_text_resize_bigger_size), sG.InputText(dft_resize_bigger_size, size=[5, 1],
                                                                                 key='it_resize_bigger_length')],
            [sG.Text('    '), sG.Text(gui_text_resize_jpeg_compression), sG.InputText(dft_jpeg_compression, size=[3, 1],
                                                                                      key='it_resize_jpeg_compression')]
        ], key='f_copy_mode')],
        [sG.Submit(gui_text_start, key='b_start')],
        [sG.ProgressBar(100, visible=False, key='pb_progress', size=[60, 15])],
        [sG.Text('postep               ', key='t_progress', visible=False)],
        [sG.Output(size=[100, 15], visible=False, key='o_output')],
        [sG.Button('OK', visible=False, key='b_finished')]
    ]
    window = sG.Window('Photos Timestamp Sorter', layout, element_justification='center', resizable=True)
    while True:
        event, values = window.read(timeout=100)
        if event != '__TIMEOUT__':
            debug_print(event, values)
        if event is None:
            break
        elif event is 'b_in_dir':
            in_dirs.append(values['b_in_dir'])
            in_dirs = list(dict.fromkeys(in_dirs))
            window.FindElement('lb_in_dirs').Update(in_dirs)
        elif event is 'b_in_dir_delete':
            in_dirs.remove(values['lb_in_dirs'][0])
            window.FindElement('lb_in_dirs').Update(in_dirs)
        elif event is 'b_start':
            success, error_message = validate_data(in_dirs, values['it_out_dir'], values['r_resize'],
                                                   values['it_resize_bigger_length'],
                                                   values['it_resize_jpeg_compression'])
            if success:
                show_progress(window)
                threading.Thread(target=copy_and_rename_dirs_images_in_queue,
                                 args=(in_dirs, values['it_out_dir'], bool(values['r_resize']),
                                       int(values['it_resize_bigger_length']),
                                       int(values['it_resize_jpeg_compression']),
                                       gui_queue), daemon=True).start()
            else:
                sG.Popup(error_message, title=gui_text_validation_title)
        elif event is 'b_finished':
            window.close()
            show_main_window()

        try:
            queue_message = gui_queue.get_nowait()
        except queue.Empty:
            queue_message = None
        if queue_message:
            if queue_message[0] == 'working':
                debug_print('progress ' + str(queue_message[1]) + '/' + str(queue_message[2]))
                window.FindElement('t_progress').Update(gui_text_progress % (queue_message[1], queue_message[2]))
                window.FindElement('pb_progress').UpdateBar(queue_message[1], queue_message[2])
            elif queue_message[0] == 'done':
                window.FindElement('t_progress').Update(gui_text_done)
                window.FindElement('b_finished').Update(visible=True)


def show_progress(window):
    debug_print('show_progress')
    window.FindElement('f_in_dirs').hide_row()
    window.FindElement('f_out_dir').hide_row()
    window.FindElement('f_copy_mode').hide_row()
    window.FindElement('b_start').hide_row()
    window.FindElement('t_progress').Update(visible=True)
    window.FindElement('pb_progress').Update(visible=True)
    window.FindElement('o_output').Update(visible=True)
    window.FindElement('b_finished').Update(visible=False)


def validate_data(src_dir_paths: List[str], dest_dir_path: str, resize_images: bool, resize_bigger_length: int,
                  resize_jpeg_compression: int) -> (bool, str):
    if len(src_dir_paths) == 0:
        return False, gui_text_validation_in_dir_no_dirs
    for d in src_dir_paths:
        if not os.path.exists(d) or os.path.isfile(d):
            return False, gui_text_validation_in_dir % d
    if dest_dir_path == '':
        return False, gui_text_validation_out_dir_no_dir
    if not os.path.exists(dest_dir_path) or os.path.isfile(dest_dir_path):
        return False, gui_text_validation_out_dir
    if dest_dir_path in src_dir_paths:
        return False, gui_text_validation_out_dir_in_in_dirs
    if resize_images:
        try:
            int(resize_bigger_length)
        except ValueError:
            return False, gui_text_validation_bigger_size
        try:
            value = int(resize_jpeg_compression)
            if value < 1 or value > 95:
                return False, gui_text_validation_jpeg_compression
        except ValueError:
            return False, gui_text_validation_jpeg_compression

    return True, None


def copy_and_rename_dirs_images_in_queue(src_dir_paths: List[str], dest_dir_path: str, resize_images: bool,
                                         resize_bigger_length: int, resize_jpeg_compression: int, gui_queue):
    debug_print('copy_and_rename_dirs_images_in_queue')
    copy_and_rename_dirs_images(src_dir_paths, dest_dir_path, lambda i, count: gui_queue.put(['working', i, count]),
                                resize_images, resize_bigger_length, resize_jpeg_compression)
    gui_queue.put(['done'])


def copy_and_rename_dirs_images(src_dir_paths: List[str], dest_dir_path: str, on_progress_updated: function,
                                resize_images: bool = False, resize_bigger_length: int = 4000,
                                resize_jpeg_compression: int = 95):
    debug_print('copy_and_rename_dirs_images')
    all_files_count = 0
    current_file = 0
    for src_dir_path in src_dir_paths:
        all_files_count += len(os.listdir(src_dir_path))

    # noinspection PyUnusedLocal
    def on_update(i, count):
        nonlocal current_file
        current_file = current_file + 1
        on_progress_updated(current_file, all_files_count)

    for src_dir_path in src_dir_paths:
        print(gui_text_progress_current_dir % src_dir_path)
        copy_and_rename_dir_images(src_dir_path, dest_dir_path, on_update, resize_images, resize_bigger_length,
                                   resize_jpeg_compression)


def copy_and_rename_dir_images(src_dir_path: str, dest_dir_path: str, on_progress_updated: function,
                               resize_images: bool = False, resize_bigger_length: int = 4000,
                               resize_jpeg_compression: int = 95):
    debug_print('copy_and_rename_dir_images')
    src_file_list = os.listdir(src_dir_path)
    src_file_count = len(src_file_list)
    for i in range(0, src_file_count):
        on_progress_updated(i + 1, src_file_count)
        src_file_name = src_file_list[i]
        src_file_path = os.path.join(src_dir_path, src_file_name)
        if os.path.isdir(src_file_path):
            print(gui_text_progress_warn_is_directory % src_file_name)
            continue
        try:
            src_img = Image.open(src_file_path)
            # get EXIF tag DATE_TIME_ORIGINAL
            # noinspection PyProtectedMember
            exif_tags = src_img._getexif()
            if exif_tags is None:
                print(gui_text_progress_warn_no_timestamp % src_file_name)
                continue
            timestamp = datetime.datetime.strptime(exif_tags[36867], '%Y:%m:%d %H:%M:%S').timestamp()
            dest_file_path = get_free_filename_for_timestamp(dest_dir_path, timestamp)

            if resize_images:
                ratio = resize_bigger_length / max(src_img.size)
                if ratio > 1.0:
                    img_resized = src_img
                else:
                    new_size = tuple(int(ratio * x) for x in src_img.size)
                    img_resized = src_img.resize(new_size, resample=Image.LANCZOS)
                img_resized.save(dest_file_path, "JPEG", quality=resize_jpeg_compression,
                                 exif=src_img.info['exif'])
            else:
                shutil.copy2(src_file_path, dest_file_path)
        except IOError as e:
            if str(e).startswith('cannot identify image file'):
                print(gui_text_progress_warn_not_compatible_image % src_file_name)
            else:
                print(e)
        except KeyError:
            print(gui_text_progress_warn_no_timestamp % src_file_name)


def get_free_filename_for_timestamp(dest_dir_path: str, timestamp, i: int = 1) -> str:
    dest_file_path = os.path.join(dest_dir_path, '%d.jpg' % timestamp if i == 1 else '%d_%d.jpg' % (timestamp, i))
    if os.path.exists(dest_file_path):
        return get_free_filename_for_timestamp(dest_dir_path, timestamp, i + 1)
    return dest_file_path


def debug_print(*argv):
    if debug:
        print(*argv)


if __name__ == '__main__':
    main()

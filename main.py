import gettext
import locale
import os
import queue
import threading

import PySimpleGUI as sG

from FilesCopier import FilesCopier, InformationType

el = gettext.translation('main', localedir='locales',
                         languages=['pl'] if locale.getdefaultlocale()[0][:2] == 'pl' else ['en'])
el.install()
_ = el.gettext

debug = False

defaults = {
    'in_dir': '',
    'out_dir': '',
    'resize_bigger_size': 2000,
    'jpeg_compression': 95
}


def main():
    show_main_window()


def show_main_window():
    gui_queue = queue.Queue()
    # All the stuff inside your window.
    layout = [
        [sG.Frame(_("Source directory:"), [
            [sG.InputText(key='it_in_dir', default_text=defaults['in_dir'], size=[102, 1])],
            [sG.FolderBrowse(_("Browse..."), key='b_in_dir', target='it_in_dir')]
        ], element_justification='right', key='f_in_dir')],
        [sG.Frame(_("Destination directory (if empty source directory will be used):"), [
            [sG.InputText(key='it_out_dir', default_text=defaults['out_dir'], size=[102, 1])],
            [sG.FolderBrowse(_("Browse..."), key='b_out_dir', target='it_out_dir')]
        ], element_justification='right', key='f_out_dir')],
        [sG.Frame(_("Options"), [
            [sG.Checkbox(_('Move files instead of copying (if source and destination directories are the same files '
                           'always will be moved)'), key='ch_move_files', default=True)],
            [sG.Checkbox(_('Rename images to creation date (if possible)'), key='ch_rename_to_timestamp',
                         default=True)],
            [sG.Checkbox(_('Resize images'), key='ch_resize', default=True)],
            [sG.Text('    '), sG.Text(_("Bigger side size (in px)")),
             sG.InputText(defaults['resize_bigger_size'], size=[5, 1], key='it_resize_bigger_length')],
            [sG.Text('    '), sG.Text(_("JPEG compression (1-95)")),
             sG.InputText(defaults['jpeg_compression'], size=[3, 1], key='it_resize_jpeg_compression')]
        ], key='f_copy_mode')],
        [sG.Submit(_("START"), key='b_start')],
        [sG.ProgressBar(100, visible=False, key='pb_progress', size=[60, 15])],
        [sG.Text('postep               ', key='t_progress', visible=False)],
        [sG.Output(size=[100, 15], visible=False, key='o_output')],
        [sG.Button('OK', visible=False, key='b_finished')]
    ]
    window = sG.Window('Photos Sorter', layout, element_justification='center', resizable=True)
    while True:
        event, values = window.read(timeout=100)
        if event != '__TIMEOUT__':
            debug_print(event, values)
        if event is None:
            break
        elif event is 'b_start':
            success, error_message = validate_data(values['it_in_dir'], values['it_out_dir'], values['ch_resize'],
                                                   values['it_resize_bigger_length'],
                                                   values['it_resize_jpeg_compression'])
            if success:
                show_progress(window)
                threading.Thread(target=iterate_dir_in_queue,
                                 args=(values['it_in_dir'], values['it_out_dir'],
                                       bool(values['ch_move_files']),
                                       bool(values['ch_rename_to_timestamp']),
                                       bool(values['ch_resize']),
                                       int(values['it_resize_bigger_length']),
                                       int(values['it_resize_jpeg_compression']),
                                       gui_queue), daemon=True).start()
            else:
                sG.Popup(error_message, title=_("Validation error"))
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
                window.FindElement('t_progress').Update(_("File %d/%d") % (queue_message[1], queue_message[2]))
                window.FindElement('pb_progress').UpdateBar(queue_message[1], queue_message[2])
            elif queue_message[0] == 'info':
                display_info(queue_message[1], queue_message[2], queue_message[3])
            elif queue_message[0] == 'done':
                window.FindElement('t_progress').Update(_("Done"))
                window.FindElement('b_finished').Update(visible=True)


def display_info(info_type: InformationType, filename: str, text: str):
    text_to_print = ''
    if info_type == InformationType.IS_DIRECTORY:
        text_to_print = _('"{filename}" subdirectory skipped')
    elif info_type == InformationType.IMAGE_WITHOUT_CREATION_DATE:
        text_to_print = _('"{filename}" does not contain creation date - won\'t be renamed')
    elif info_type == InformationType.IMAGE_ERROR:
        text_to_print = _('"{filename}" processing image failed: {text}')
    elif info_type == InformationType.DESTINATION_ALREADY_EXISTS:
        text_to_print = _('"{filename}" destination file already exists')
    elif info_type == InformationType.MOVING_ERROR:
        text_to_print = _('"{filename}" moving file failed: {text}')
    elif info_type == InformationType.PANORAMIC_IMAGE:
        text_to_print = _('"{filename}" seems to be panoramic image - it won\'t be resized')
    print(text_to_print.format(filename=filename, text=text))


def show_progress(window):
    debug_print('show_progress')
    window.FindElement('f_in_dir').hide_row()
    window.FindElement('f_out_dir').hide_row()
    window.FindElement('f_copy_mode').hide_row()
    window.FindElement('b_start').hide_row()
    window.FindElement('t_progress').Update(visible=True)
    window.FindElement('pb_progress').Update(visible=True)
    window.FindElement('o_output').Update(visible=True)
    window.FindElement('b_finished').Update(visible=False)


def validate_data(src_dir_path: str, dest_dir_path: str, resize_images: bool, resize_bigger_length: int,
                  resize_jpeg_compression: int) -> (bool, str):
    if dest_dir_path == '':
        dest_dir_path = src_dir_path

    if src_dir_path == '':
        return False, _('Set source directory')
    if not os.path.exists(src_dir_path) or os.path.isfile(src_dir_path):
        return False, _('Source directory does not exists or is not a directory')
    if dest_dir_path == '':
        return False, _('Set destination dir')
    if not os.path.exists(dest_dir_path) or os.path.isfile(dest_dir_path):
        return False, _('Destination directory does not exists or is not a directory')
    if resize_images:
        try:
            int(resize_bigger_length)
        except ValueError:
            return False, _('Bigger size size must be an integer')
        try:
            value = int(resize_jpeg_compression)
            if value < 1 or value > 95:
                return False, _('JPEG compression must be an integer in range 1-95')
        except ValueError:
            return False, _('JPEG compression must be an integer in range 1-95')

    return True, None


def iterate_dir_in_queue(src_dir_path: str, dest_dir_path: str, move_files: bool, rename_to_creation_date: bool,
                         resize_images: bool, resize_bigger_length: int, resize_jpeg_compression: int,
                         gui_queue):
    debug_print('copy_and_rename_dir_images_in_queue')

    if dest_dir_path == '':
        dest_dir_path = src_dir_path

    files_copier = FilesCopier(move_files, rename_to_creation_date, resize_images, resize_bigger_length,
                               resize_jpeg_compression, debug,
                               lambda info_type, filename, text: gui_queue.put(['info', info_type, filename, text]))
    files_copier.iterate_dir(src_dir_path, dest_dir_path, lambda i, count: gui_queue.put(['working', i, count]))

    gui_queue.put(['done'])


def debug_print(*argv):
    if debug:
        print(*argv)


if __name__ == '__main__':
    main()

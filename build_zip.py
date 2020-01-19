import os
import shutil
import subprocess
import sys
import zipfile


def main():
    new_name = 'PhotosSorter'
    if len(sys.argv) == 2:
        new_name = new_name + '_' + sys.argv[1]
    p = subprocess.Popen(['pyinstaller', 'main.spec'], stdout=subprocess.PIPE, bufsize=1)
    for line in iter(p.stdout.readline, b''):
        print(line)
    p.stdout.close()
    p.wait()
    shutil.move(os.path.join('dist', 'main', 'main.exe'), os.path.join('dist', 'main', new_name + '.exe'))
    shutil.move(os.path.join('dist', 'main'), os.path.join('dist', new_name))
    zip(new_name)
    shutil.rmtree(os.path.join('dist', new_name))


def zip(new_name: str):
    zipf = zipfile.ZipFile(os.path.join('dist', new_name + '.zip'), 'w', zipfile.ZIP_DEFLATED)
    path = os.path.join('dist', new_name)
    for root, dirs, files in os.walk(path):
        for file in files:
            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(path, '..')))
    zipf.close()


if __name__ == '__main__':
    main()

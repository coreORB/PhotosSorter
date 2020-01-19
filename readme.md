# Photos Sorter
python script

## Building exe:
Build executable to zip: 
```
$ npm install pyinstaller
$ build_zip.py 1_0
```

## Translations:
Generate languages template:
```
C:\Users\<user>\AppData\Local\Programs\Python\Python37-32\Tools\i18n\pygettext.py -d main -o locales/main.pot main.py
```

Build translations:
```
cd locales\en\LC_MESSAGES
C:\Users\<user>\AppData\Local\Programs\Python\Python37-32\Tools\i18n\msgfmt.py -o main.mo main
cd locales\pl\LC_MESSAGES
C:\Users\<user>\AppData\Local\Programs\Python\Python37-32\Tools\i18n\msgfmt.py -o main.mo main
```

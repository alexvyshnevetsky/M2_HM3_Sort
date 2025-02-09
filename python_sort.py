
'''
This program is used to automatically sort files in a user-defined directory.

Files will be sorted as follows:
images ('JPEG', 'PNG', 'JPG', 'SVG')
documents ('DOC', 'DOCX', 'TXT', 'PDF', 'XLSX', 'PPTX' )
audio ('MP3', 'OGG', 'WAV', 'AMR')
video ('AVI', 'MP4', 'MOV', 'MKV')
archives ('ZIP', 'GZ', 'TAR')
python ('.py')
other 

To start the program, write the address of the directory to be sorted in the command line.

Example of a line to run the program: python .\python_sort.py -s 'C:/Folder/Next_folder/Destination_Folder'

'''

import argparse
from pathlib import Path
import shutil
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


parser = argparse.ArgumentParser(description='Sort data in folder')
parser.add_argument('--source', '-s', required=True, help='Write destination in format "C:/Folder/Next_folder/Destination_Folder"')
args = vars(parser.parse_args())
sourse = args.get('source')

DESTINATION = Path(sourse)

directive_extension = {
    'images': ['.jpeg', '.png', '.jpg', '.svg'],
    'documents': ['.doc', '.docx', '.txt', '.pdf', '.xlsx', '.pptx'],
    'audio': ['.mp3', '.ogg', '.wav', '.amr'],
    'video': ['.avi', '.mp4', '.mov', '.mkv'],
    'archives': ['.zip', '.gz', '.tar'],
    'python': ['.py'],
    'other': []
}

CYRILLIC_SYMBOLS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяєіїґ"
TRANSLATION = ("a", "b", "v", "g", "d", "e", "e", "j", "z", "i", "j", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u",
               "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya", "je", "i", "ji", "g")

TRANS = {ord(c): t for c, t in zip(CYRILLIC_SYMBOLS + CYRILLIC_SYMBOLS.upper(), TRANSLATION + tuple(t.upper() for t in TRANSLATION))}


lock = threading.Lock()


def normalize(name: str):
    translate_name = name.translate(TRANS)
    return re.sub(r'\W', '_', translate_name)


def log_action(action_type, message, directory):
    with open(directory / 'logs.txt', 'a', encoding='utf-8') as logs:
        logs.write(f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | {action_type}: {message}\n")


def ensure_dest_exists(dest_dir: Path):
    if not dest_dir.exists():
        with lock: 
            dest_dir.mkdir(parents=True, exist_ok=True)


def move_elements(file: Path):
    if file.is_file():
        ext = file.suffix.lower()
        for folder, extensions in directive_extension.items():
            if ext in extensions:
                dest_dir = DESTINATION / folder
                ensure_dest_exists(dest_dir) 
                dest_file = dest_dir / file.name

                try:
                    shutil.move(str(file), str(dest_file))
                    log_action('Move', f"{file} -> {dest_file}", DESTINATION)
                    nn = file.stem
                    new_name = normalize(nn) + ext
                    new_file_dest = dest_dir / new_name
                    shutil.move(str(dest_file), str(new_file_dest))
                    log_action('Rename', f"{dest_file} -> {new_file_dest}", DESTINATION)
                except FileNotFoundError as e:
                    log_action('Error', f"File not found during move operation: {file} -> {dest_file}. Error: {e}", DESTINATION)
                except Exception as e:
                    log_action('Error', f"Error during file move: {file}. Error: {e}", DESTINATION)
                return


        dest_dir = DESTINATION / 'other'
        ensure_dest_exists(dest_dir) 
        dest_file = dest_dir / file.name

        try:
            shutil.move(str(file), str(dest_file))
            log_action('Move', f"{file} -> {dest_file}", DESTINATION)
            nn = file.stem
            new_name = normalize(nn) + ext
            new_file_dest = dest_dir / new_name
            shutil.move(str(dest_file), str(new_file_dest))
            log_action('Rename', f"{dest_file} -> {new_file_dest}", DESTINATION)
        except FileNotFoundError as e:
            log_action('Error', f"File not found during move operation: {file} -> {dest_file}. Error: {e}", DESTINATION)
        except Exception as e:
            log_action('Error', f"Error during file move: {file}. Error: {e}", DESTINATION)


def read_folder(path: Path, executor: ThreadPoolExecutor):
    futures = []
    for element in path.iterdir():
        if element.is_dir():
            futures.append(executor.submit(read_folder, element, executor))
        else:
            futures.append(executor.submit(move_elements, element))

   
    for future in as_completed(futures):
        future.result()


def create_new_folders(base_path: Path):
    for folder in directive_extension.keys():
        (base_path / folder).mkdir(exist_ok=True, parents=True)


def unpack_archives(directory: Path):
    for name in directory.iterdir():
        if name.suffix.lower() in ['.zip', '.gz', '.tar']:
            try:
                shutil.unpack_archive(name, directory / name.stem)
                log_action('Unpacked', f"{name} extracted", directory)
                name.unlink() 
            except Exception as e:
                log_action('Error', f"Failed to unpack {name}: {e}", directory)


def delete_empty_folders(directory: Path):
    for folder in directory.iterdir():
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
            log_action('Delete', f"Empty folder {folder} removed", directory)


attempts = 3
while attempts > 0:
    create_empty = input("Do you want to create empty folders? Enter Y or N: ").strip().lower()
    if create_empty in ('y', 'n'):       
        with ThreadPoolExecutor() as executor:
            read_folder(DESTINATION, executor) 
            unpack_archives(DESTINATION / 'archives') 
            delete_empty_folders(DESTINATION) 
            if create_empty == 'y':
                create_new_folders(DESTINATION)
        break
    else:
        attempts -= 1
        print(f"Invalid input. {attempts} attempts remaining.")

if attempts == 0:
    print("Exiting due to repeated incorrect input.")
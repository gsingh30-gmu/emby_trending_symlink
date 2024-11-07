import configparser
import os
import subprocess
import sys
import requests
import logging
import json

# Set up logging
logging.basicConfig(filename='sync.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')


def create_config_file():
    if os.path.exists('config.ini'):
        return
    config = configparser.ConfigParser()
    config['TRAKT'] = { 'trakt_api_key': 'API_KEY_HERE' }
    config['EMBY'] = {'emby_api_key': 'API_KEY_HERE',
                      'emby_url': 'http://localhost:8096'
                      }

    config['SYM_LINK_DIRECTORY_MOVIES'] = {'ORIGINAL_PATH': 'PATH_TO_MOVIES',
                                           'SYMLINK_DIRECTORY': 'PATH_TO_SYMLINK_DIRECTORY'}
    config['SYM_LINK_DIRECTORY_TV'] = {'ORIGINAL_PATH': 'PATH_TO_TV_SHOWS',
                                       'SYMLINK_DIRECTORY': 'PATH_TO_SYMLINK_DIRECTORY'}
    config['REMOTE_PATHS'] = {'remote_path_movies': 'PATH_TO_MOVIES', 'remote_path_tv': 'PATH_TO_TV_SHOWS'}

    with open('config.ini', 'w') as configfile:
        config.write(configfile)

    print('config.ini was created, fill in the required information')
    sys.exit(0)


def main():
    create_config_file()
    config = configparser.ConfigParser()
    config.read('config.ini')
    trakt_api_key = config['TRAKT']['trakt_api_key']
    sync_trending_movies(trakt_api_key)
    sync_trending_shows(trakt_api_key)


def sync_trending_movies(trakt_api_key):
    trending_movie_data = get_trakt_data(trakt_api_key, 'movie')
    if not trending_movie_data:
        logging.error("Error fetching data from Trakt")
        sys.exit(1)

    # Collect imdb_ids of trending movies
    trending_imdb_ids = set()
    for item in trending_movie_data:
        imdb_id = item['movie']['ids']['imdb']
        trending_imdb_ids.add(imdb_id)

    # Process each trending movie
    for item in trending_movie_data:
        logging.info("Processing movie: %s", item['movie']['title'])
        imdb_id = item['movie']['ids']['imdb']
        emby_path = get_emby_path(imdb_id, 'movie')
        if not emby_path:
            logging.error("Error fetching Emby path")
            continue

        # Check if the symlink already exists
        existing_symlink_mapping = get_existing_symlinks('movie')
        symlink_exists = False
        for symlink_path, symlink_imdb_id in existing_symlink_mapping.items():
            if symlink_imdb_id == imdb_id:
                symlink_exists = True
                break
        if symlink_exists:
            logging.info("Symlink already exists")
            continue

        # Create the symlink
        if not create_symlink(emby_path, 'movie', imdb_id):
            logging.error("Error creating symlink")
            continue

        logging.info("Symlink created")

    # Now remove symlinks that are no longer trending
    existing_symlink_mapping = get_existing_symlinks('movie')

    # For each existing symlink, check if it corresponds to a trending movie
    for symlink_path, symlink_imdb_id in existing_symlink_mapping.items():
        if symlink_imdb_id not in trending_imdb_ids:
            # Delete the symlink
            if delete_symlink(symlink_path, 'movie'):
                logging.info("Symlink deleted: %s", symlink_path)
            else:
                logging.error("Error deleting symlink: %s", symlink_path)


def sync_trending_shows(trakt_api_key):
    trending_tv_data = get_trakt_data(trakt_api_key, 'tv')
    if not trending_tv_data:
        logging.error("Error fetching data from Trakt")
        sys.exit(1)

    trending_imdb_ids = set()
    for item in trending_tv_data:
        imdb_id = item['show']['ids']['imdb']
        trending_imdb_ids.add(imdb_id)

    # Process each trending show
    for item in trending_tv_data:
        logging.info("Processing show: %s", item['show']['title'])
        imdb_id = item['show']['ids']['imdb']
        emby_path = get_emby_path(imdb_id, 'tv')
        if not emby_path:
            logging.error("Error fetching Emby path")
            continue

        # Check if the symlink already exists
        existing_symlink_mapping = get_existing_symlinks('tv')
        symlink_exists = False
        for symlink_path, symlink_imdb_id in existing_symlink_mapping.items():
            if symlink_imdb_id == imdb_id:
                symlink_exists = True
                break
        if symlink_exists:
            logging.info("Symlink already exists")
            continue

        # Create the symlink
        if not create_symlink(emby_path, 'tv', imdb_id):
            logging.error("Error creating symlink")
            continue

        logging.info("Symlink created")

    # Now remove symlinks that are no longer trending
    existing_symlink_mapping = get_existing_symlinks('tv')

    # For each existing symlink, check if it corresponds to a trending show
    for symlink_path, symlink_imdb_id in existing_symlink_mapping.items():
        if symlink_imdb_id not in trending_imdb_ids:
            # Delete the symlink
            if delete_symlink(symlink_path, 'tv'):
                logging.info("Symlink deleted: %s", symlink_path)
            else:
                logging.error("Error deleting symlink: %s", symlink_path)


def get_trakt_data(api_key, media_type, list_id=None, page=1, limit=50):
    base_url = "https://api.trakt.tv"
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": api_key
    }

    if list_id:
        endpoint = f"/users/me/lists/{list_id}/items"
    elif media_type.lower() == 'movie':
        endpoint = "/movies/trending"
    elif media_type.lower() == 'tv':
        endpoint = "/shows/trending"

    url = f"{base_url}{endpoint}?page={page}&limit={limit}"
    logging.info(f"Fetching data from Trakt: {url}")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error fetching data from Trakt: {response.status_code}")
        return None


def get_emby_path(id, media_type):
    config = configparser.ConfigParser()
    config.read('config.ini')
    emby_api_key = config['EMBY']['emby_api_key']
    emby_url = config['EMBY']['emby_url']

    base_url = emby_url.rstrip('/')

    headers = {
        'X-Emby-Token': emby_api_key
    }

    provider_id = id  # This should be the full provider ID, e.g., 'tt8134742' for IMDb
    if media_type.lower() == 'movie':
        provider_name = 'imdb'
    elif media_type.lower() == 'tv':
        provider_name = 'imdb'
    else:
        logging.error("Invalid media type")
        return None

    params = {
        'AnyProviderIdEquals': f'{provider_name}.{provider_id}',
        'Recursive': 'true',
        'Fields': 'Path,IsFolder'
    }

    url = f"{base_url}/emby/Items"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        items = data.get('Items', [])
        if not items:
            logging.error("No items found with the given ID")
            return None

        # Get remote_path and original_path based on media type
        if media_type.lower() == 'movie':
            remote_path = config['REMOTE_PATHS'].get('remote_path_movies')
            original_path = config['SYM_LINK_DIRECTORY_MOVIES'].get('ORIGINAL_PATH')
        elif media_type.lower() == 'tv':
            remote_path = config['REMOTE_PATHS'].get('remote_path_tv')
            original_path = config['SYM_LINK_DIRECTORY_TV'].get('ORIGINAL_PATH')
        else:
            logging.error("Invalid media type")
            return None

        selected_item = None

        if remote_path:
            for item in items:
                path = item.get('Path')
                if remote_path in path:
                    selected_item = item
                    break

        # If no item found with remote_path or remote_path not set, try with original_path
        if not selected_item:
            for item in items:
                path = item.get('Path')
                if original_path and path.startswith(original_path):
                    selected_item = item
                    break

        if selected_item:
            path = selected_item.get('Path')
            is_folder = selected_item.get('IsFolder', False)
            # For movies, if path is a file, get its parent directory
            if media_type.lower() == 'movie' and not is_folder:
                path = os.path.dirname(path)
            # Replace remote_path with original_path if both are set
            if remote_path and original_path:
                adjusted_path = path.replace(remote_path, original_path)
                return adjusted_path
            else:
                # If remote_path not set, return the path as is
                return path
        else:
            logging.error("No item found matching the remote_path or original_path")
            return None
    else:
        logging.error(f"Error fetching item from Emby: {response.status_code}")
        return None


def get_imdb_id_by_emby_path(path):
    config = configparser.ConfigParser()
    config.read('config.ini')
    emby_api_key = config['EMBY']['emby_api_key']
    emby_url = config['EMBY']['emby_url']

    base_url = emby_url.rstrip('/')

    headers = {
        'X-Emby-Token': emby_api_key
    }

    params = {
        'Path': path,
        'Fields': 'ProviderIds'
    }

    url = f"{base_url}/emby/Items"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        items = data.get('Items', [])
        if not items:
            logging.error(f"No items found in Emby with path {path}")
            return None
        item = items[0]  # Assuming the first item is correct
        provider_ids = item.get('ProviderIds', {})
        imdb_id = provider_ids.get('Imdb')
        if imdb_id:
            return imdb_id
        else:
            logging.error(f"No IMDb ID found for item with path {path}")
            return None
    else:
        logging.error(f"Error fetching item from Emby by path: {response.status_code}")
        return None


def create_symlink(file_path, media_type, imdb_id):
    config = configparser.ConfigParser()
    config.read('config.ini')

    if media_type.lower() == 'movie':
        symlink_dir = config['SYM_LINK_DIRECTORY_MOVIES'].get('SYMLINK_DIRECTORY')
        original_path = config['SYM_LINK_DIRECTORY_MOVIES'].get('ORIGINAL_PATH')
        mapping_file = 'symlinks_movie.json'
    elif media_type.lower() == 'tv':
        symlink_dir = config['SYM_LINK_DIRECTORY_TV'].get('SYMLINK_DIRECTORY')
        original_path = config['SYM_LINK_DIRECTORY_TV'].get('ORIGINAL_PATH')
        mapping_file = 'symlinks_tv.json'
    else:
        logging.error("Invalid media type")
        return False

    if not symlink_dir:
        logging.error("SYMLINK_DIRECTORY not set in config")
        return False

    if not os.path.exists(symlink_dir):
        os.makedirs(symlink_dir)

    if file_path.startswith(original_path):
        relative_path = os.path.relpath(file_path, original_path)
    else:
        logging.error("file_path does not start with ORIGINAL_PATH")
        return False

    symlink_path = os.path.join(symlink_dir, relative_path)

    symlink_dirname = os.path.dirname(symlink_path)
    if not os.path.exists(symlink_dirname):
        os.makedirs(symlink_dirname)

    if os.name == 'nt':  # Windows
        # Use cmd.exe to execute mklink
        command = ['cmd', '/c', 'mklink', '/J', symlink_path, file_path]
        try:
            # Execute the command
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"Symlink created: {symlink_path} -> {file_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating symlink: {e.stderr.decode().strip()}")
            return False
    else:
        # Non-Windows systems
        try:
            os.symlink(file_path, symlink_path)
            logging.info(f"Symlink created: {symlink_path} -> {file_path}")
        except OSError as e:
            logging.error(f"Error creating symlink: {e}")
            return False

    # Record the mapping of symlink_path to imdb_id
    mapping = {}
    if os.path.exists(mapping_file):
        with open(mapping_file, 'r') as f:
            mapping = json.load(f)
    mapping[symlink_path] = imdb_id
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f)

    return True


def delete_symlink(symlink_path, media_type):
    config = configparser.ConfigParser()
    config.read('config.ini')

    if media_type.lower() == 'movie':
        mapping_file = 'symlinks_movie.json'
    elif media_type.lower() == 'tv':
        mapping_file = 'symlinks_tv.json'
    else:
        logging.error("Invalid media type")
        return False

    if os.path.islink(symlink_path) or (os.name == 'nt' and os.path.isdir(symlink_path)):
        try:
            if os.path.isdir(symlink_path):
                os.rmdir(symlink_path)
            else:
                os.unlink(symlink_path)
            logging.info(f"Symlink deleted: {symlink_path}")

            mapping = {}
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
            if symlink_path in mapping:
                del mapping[symlink_path]
                with open(mapping_file, 'w') as f:
                    json.dump(mapping, f)

            return True
        except OSError as e:
            logging.error(f"Error deleting symlink: {e}")
            return False
    else:
        logging.warning(f"No symlink found at {symlink_path}")
        return False


def get_existing_symlinks(media_type):
    config = configparser.ConfigParser()
    config.read('config.ini')

    if media_type.lower() == 'movie':
        symlink_dir = config['SYM_LINK_DIRECTORY_MOVIES'].get('SYMLINK_DIRECTORY')
        mapping_file = 'symlinks_movie.json'
    elif media_type.lower() == 'tv':
        symlink_dir = config['SYM_LINK_DIRECTORY_TV'].get('SYMLINK_DIRECTORY')
        mapping_file = 'symlinks_tv.json'
    else:
        logging.error("Invalid media type")
        return {}

    if not symlink_dir:
        logging.error("SYMLINK_DIRECTORY not set in config")
        return {}

    symlink_mapping = {}

    if os.path.exists(mapping_file):
        with open(mapping_file, 'r') as f:
            symlink_mapping = json.load(f)
    else:
        for root, dirs, files in os.walk(symlink_dir):
            for name in dirs:
                symlink_path = os.path.join(root, name)
                if os.path.islink(symlink_path) or (os.name == 'nt' and os.path.isdir(symlink_path)):
                    # Try to get the imdb_id
                    target_path = symlink_path  # For Windows
                    imdb_id = get_imdb_id_by_emby_path(target_path)
                    if imdb_id:
                        symlink_mapping[symlink_path] = imdb_id
        with open(mapping_file, 'w') as f:
            json.dump(symlink_mapping, f)
    return symlink_mapping


main()

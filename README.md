# Trending Media Sync for Emby

This script synchronizes trending movies and TV shows from [Trakt.tv](https://trakt.tv/) with your [Emby](https://emby.media/) media server. It checks if the trending content is available in your library and creates symbolic links to a designated folder. This allows you to create a new Emby library showcasing popular/trending media, displaying them on the home dashboard for all users.

This script is only tested with Windows, but should work on Unix-like operating systems with a few changes.
## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Logging](#logging)

## Features

- Fetches trending movies and TV shows from Trakt.tv.
- Checks for the availability of trending media in your Emby library.
- Creates symbolic links to the available media in a specified directory.
- Enables the creation of a new Emby library for trending content.
- Automatically updates the symbolic links based on the latest trending data.
- Supports both Windows and Unix-like operating systems.

## Prerequisites

- Python 3.6 or higher
- Emby media server with API access
- Trakt.tv account with API access
- Permissions to create symbolic links

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/gsingh30-gmu/emby_trending_symlink.git
   cd emby-trending-sync
   ```

2. **Install required Python packages:**

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Create the configuration file:**

   Run the script once to generate a `config.ini` file:

   ```bash
   python sync.py
   ```

   The script will create a `config.ini` file and exit.

2. **Edit the `config.ini` file:**

   Open `config.ini` in a text editor and fill in the required information:

   ```ini
   [TRAKT]
   trakt_api_key = YOUR_TRAKT_API_KEY
   trakt_custom_lists =  # Optional: Comma-separated list IDs
   
   [EMBY]
   emby_api_key = YOUR_EMBY_API_KEY
   emby_url = http://localhost:8096  # Replace with your Emby server URL

   [SYM_LINK_DIRECTORY_MOVIES]
   ORIGINAL_PATH = /path/to/your/movies
   SYMLINK_DIRECTORY = /path/to/your/symlink/movies

   [SYM_LINK_DIRECTORY_TV]
   ORIGINAL_PATH = /path/to/your/tvshows
   SYMLINK_DIRECTORY = /path/to/your/symlink/tvshows

   [REMOTE_PATHS]
   remote_path_movies = /remote/path/to/movies  # Optional if Emby is using a different path (i.e. docker)
   remote_path_tv = /remote/path/to/tvshows     # Optional
   ```

   - **TRAKT Section:**
     - `trakt_api_key`: Your Trakt.tv API key.
     - `trakt_custom_lists`: (Optional) Comma-separated list IDs if you want to sync custom lists.

   - **EMBY Section:**
     - `emby_api_key`: Your Emby API key.
     - `emby_url`: The base URL of your Emby server.

   - **SYM_LINK_DIRECTORY_MOVIES & SYM_LINK_DIRECTORY_TV Sections:**
     - `ORIGINAL_PATH`: The path where your movies or TV shows are stored.
     - `SYMLINK_DIRECTORY`: The path where the symbolic links will be created.

   - **REMOTE_PATHS Section:**
     - `remote_path_movies` and `remote_path_tv`: (Optional) Use these if your Emby server uses different paths than your file system (e.g., when using network shares).

## Usage

Run the script to start creating symbolic links for trending media:

```bash
python sync.py
```

The script will:

1. Fetch the list of trending movies and TV shows from Trakt.tv.
2. Check if each trending item exists in your Emby library.
3. Create symbolic links for available media in the specified directories.
4. Remove symbolic links for media that are no longer trending.

### Scheduling Automatic Sync

To keep your trending library up to date, schedule the script to run at regular intervals:

- **On Windows (using Task Scheduler):**

  - Open Task Scheduler.
  - Create a new task with the following settings:
    - **Action:** Start a program
    - **Program/script:** `python`
    - **Add arguments:** `C:\path\to\emby-trending-sync\sync.py`
    - **Trigger:** Daily at your preferred time.

## Logging

The script generates a `sync.log` file in the same directory. It contains detailed logs of each operation, including errors and informational messages.


---

*Disclaimer: This project is not affiliated with Trakt.tv or Emby.*
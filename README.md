# Nuggit: Small bits of insights from GitHub repositories

Nuggit is a Python tool that creates an index-card like summary of a GitHub repository.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/9c83975c-2139-4ee6-9e7a-6cbcb687792e">

## Installation

Using virtual environments to manage requirements:
```bash
:~$ git clone https://github.com/verovaleros/nuggit.git
:~$ cd nuggit/
:~$ python3 -m venv .venv
:~$ source .venv/bin/activate
:~$ pip install -r requirements.txt
```

## Usage
```python
:~$ python3 nuggit.py --help
usage: nuggit.py [-h] -r REPO [-l LOG_FILE] [-d] [-v]

Nuggit: Small bits of big insights from GitHub repositories

optional arguments:
  -h, --help            show this help message and exit
  -r REPO, --repo REPO  URL of the GitHub repository to analyze.
  -l LOG_FILE, --log_file LOG_FILE
                        Log file name (default: nuggit.log)
  -d, --debug           Extra verbose for debugging.
  -v, --verbose         Be verbose```
```

### Docker

Run nuggit via Docker with:

```bash
:~$ docker run -ti -v $(pwd)/nuggit/.env:/nuggit/.env:ro -v $(pwd)/nuggit/output:/nuggit/output/ -v $(pwd)/nuggit/logs:/nuggit/logs ghcr.io/verovaleros/nuggit:latest python3 nuggit.py -r https://github.com/verovaleros/nuggit
```

## About
This tool was created by verovaleros on October 2024. GNU General Public License v2.0.

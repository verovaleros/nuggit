import argparse
import logging
import sys
import os
from dotenv import load_dotenv
from util.github import validate_repo_url
from util.github import get_repo_info
from util.github import get_repo_latest_release
from util.db import initialize_database
from util.db import insert_or_update_repo
from rich.console import Console
from rich.table import Table


def setup_logging(log_file, log_level):
    """
    Use logging to output to a file and the standard output.
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create file handler which logs messages to a file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)

    # Create console handler which logs messages to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create formatter and set it for both handlers
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def main():

    parser = argparse.ArgumentParser(description="Nuggit: Small bits of big insights from GitHub repositories")
    parser.add_argument('-r', '--repo',
                        required=True,
                        help="URL of the GitHub repository to analyze.")
    parser.add_argument('-l', '--log_file',
                        required=False,
                        help='Log file name (default: logs/nuggit.log)',
                        default='logs/nuggit.log')
    parser.add_argument('-d', '--debug',
                        required=False,
                        help="Extra verbose for debugging.",
                        action="store_const",
                        dest="log_level",
                        const=logging.DEBUG,
                        default=logging.ERROR,)
    parser.add_argument('-v', '--verbose',
                        required=False,
                        help="Be verbose",
                        action="store_const",
                        dest="log_level",
                        const=logging.INFO,)

    args = parser.parse_args()

    setup_logging(args.log_file, args.log_level)

    # Load the .env file
    load_dotenv()
    github_token = os.getenv('GITHUB_TOKEN')

    if not github_token:
        logging.error("GitHub token not found in .env file.")
        sys.exit(1)

    owner, repository = validate_repo_url(args.repo)
    if not owner:
        logging.error(f"Invalid repository URL: {args.repo}")
        sys.exit(1)

    logging.info(f"Starting analysis of repository: {args.repo}")
    initialize_database()

    repo_info = get_repo_info(owner, repository, github_token)

    insert_or_update_repo(repo_info)

    console = Console(record=True)

    table = Table(title="Nuggit Repository Information", row_styles=["reverse", ""])

    # Set max_width for columns
    table.add_column(repo_info["name"], style="cyan", no_wrap=True, width=15)
    table.add_column(repo_info["url"], style="magenta", width=60, overflow="fold")

    table.add_row("About", repo_info["description"])
    table.add_row("Topics", repo_info["topics"])
    table.add_row("License", repo_info["license"])
    table.add_row("Latest Release", get_repo_latest_release(owner + "/" + repository))
    table.add_row("Stars", str(repo_info["stars"]))
    table.add_row("Forks", str(repo_info["forks"]))
    table.add_row("Issues", str(repo_info["issues"]))
    table.add_row("Contributors", str(repo_info["contributors"]))
    table.add_row("Commits", str(repo_info["commits"]))

    console.print(table)

    # Save the console output to an HTML file
    console.save_html("output/" + repo_info["name"] + ".html", inline_styles=True)


if __name__ == "__main__":
    main()

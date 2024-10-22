import argparse
import logging
import sys
import os
from dotenv import load_dotenv
from util.github import validate_repo_url


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
                        help='Log file name (default: nuggit.log)',
                        default='nuggit.log')
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
        logging.error(f"Invalid repository URL: {args.repo}")
        sys.exit(1)

    logging.info(f"Starting analysis of repository: {args.repo}")


if __name__ == "__main__":
    main()


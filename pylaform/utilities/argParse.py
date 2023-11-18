import argparse


def argument_parser():
    """
    Takes command line input and generates a resume based on the template specified
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--template",
        type=str,
        required=False,
        choices=['one-page', 'hybrid' 'chronological', 'functional'],
        help="specifies which template type to generate",
    )

    return parser.parse_args()

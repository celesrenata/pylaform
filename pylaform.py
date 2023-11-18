from pylaform.utilities.argParse import argument_parser
from pylaform.templates import onePage


def main():
    """
    Pylaform is a resume generator backed by mariadb
    :return: None
    """

    args = argument_parser()

    match str(args.template):
        case "one-page":
            generator = onePage.Generator()
            generator.run()
        case "hybrid":
            # generator = onePager.Generator()
            # generator.run()
            print("Coming Soon!")
        case "chronological":
            # generator = onePager.Generator()
            # generator.run()
            print("Coming Soon!")
        case "functional":
            # generator = onePager.Generator()
            # generator.run()
            print("Coming Soon!")
        case _:
            print("Run --help argument for options")


if __name__ == "__main__":
    main()

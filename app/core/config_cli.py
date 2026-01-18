import argparse


ACTION_CHICES = [
    '',
]


def configure_cli_parser(
    available_modes,
):
    parser = argparse.ArgumentParser(
        'Приложение для отслеживания инфляции на основе покупок.',
    )
    parser.add_argument(
        'mode',
        choices=available_modes,
        help='Режим работы приложения.',
    )

    return parser

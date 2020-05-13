from .google_client import GoogleAccount, FileSystemTokenBackend
from .static import (
    default_account_name,
    default_client,
    default_redirect_url,
)

# import types


def init(args, init=True):
    credentials, redirect_url = select_app(args)
    token_backend = get_token_backend(args)

    account = GoogleAccount(
        credentials, token_backend=token_backend, proxies=args.proxies,
    )
    if init:
        account.authenticate(
            scope="https://www.googleapis.com/auth/drive", redirect_url=redirect_url,
        )

    return account


def get_save_name(args):

    if not args.save_account_name:
        args.save_account_name = default_account_name

    if args.app is not None:
        args.save_account_name += "_app_" + str(args.app)

    return args.save_account_name


def select_app(args):
    if args.client_id and args.client_secret and args.redirect_url:
        credentials = (args.client_id, args.client_secret)
        redirect_url = args.redirect_url
        args.app = None
    elif hasattr(args, "clients"):
        client = args.clients[args.app]
        credentials = (client.get("client_id"), client.get("client_secret"))
        redirect_url = client.get("redirect_url")
    else:
        credentials = default_client
        redirect_url = default_redirect_url
        args.app = None
    return credentials, redirect_url


def get_token_backend(args):
    token_backend = FileSystemTokenBackend(
        token_dir=args.save_dir, token_filename=get_save_name(args) + "_token.json"
    )
    return token_backend

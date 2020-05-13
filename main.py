from googledrivepure.account import do_init
from googledrivepure.upload import do_upload
from googledrivepure.args import parse_args
from googledrivepure.utils import help_func


def main():
    args = parse_args()

    def get_proxies():
        return args.proxies

    help_func.get_proxies = get_proxies

    client = do_init(args, init=(args.mode == "init"))
    if args.mode == "upload":
        do_upload(client, args)

    # elif args.mode == 'put':
    #     do_put(client, args)

    # elif args.mode == 'share':
    #     do_share(client, args)

    # elif args.mode == 'direct':
    #     do_direct(client, args)

    # elif args.mode == 'delete':
    #     do_delete(client, args)

    # elif args.mode == 'mkdir':
    #     do_mkdir(client, args)

    # elif args.mode == 'move':
    #     do_move(client, args)

    # elif args.mode == 'remote':
    #     do_remote(client, args)

    # elif args.mode == 'search':
    #     do_search(client, args)

    # elif args.mode == 'quota':
    #     do_quota(client, args)


if __name__ == "__main__":
    main()
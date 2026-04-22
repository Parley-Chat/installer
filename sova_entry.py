import sys

CLI_COMMANDS={"list-users", "delete-channel", "delete-user", "help"}

if len(sys.argv)>1 and sys.argv[1] in CLI_COMMANDS:
    from cli import main
    main()
else:
    import main

def on_info(server, info):
    if info.content == "api test":
        print(server.PlayerInfoAPIR.getPlayerInfo(info.player))

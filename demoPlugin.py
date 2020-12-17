def on_info(server, info):
    if info.content == "!!APITEST":
        print(server.PlayerInfoAPIR.getPlayerInfo(info.player))

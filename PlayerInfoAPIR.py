import json
from pathlib import Path
import demjson
import os
import textwrap
from typing import Union, Any
from nbt.nbt import NBTFile, TAG_List, TAGLIST, TAG_Compound, TAG_Int_Array

debug = False


class Token:
    def __init__(self, type_, name, value, extra=None):
        self.__is_set = False
        self.type_ = type_
        self.name = name or ""
        self.__value = value if value is None else walk_nbt(value)
        self.extra = extra

        if self.type_ == TAG_Compound:
            self.keys = [x.name for x in self.__value]

        self.__is_set = True

    def __setattr__(self, key, value):
        if key == "_Token__is_set" or not self.__is_set:
            super().__setattr__(key, value)

        elif key == "_value":
            if not isinstance(self.__value, (int, str, float, list)):
                self.__value._value = value
            else:
                super().__setattr__("_value", value)

        elif hasattr(self, "keys") and key in self.keys:
            item = self[key]
            item.__value = value

    def __getattr__(self, item):
        if self.type_ == TAG_Compound and self.__is_set:
            if item in self.keys:
                return self[item]
        super().__getattribute__(item)

    def __getitem__(self, key):
        if self.type_ == TAG_Compound:
            return {x.name: x for x in self.__value}[key]
        elif self.type_ == TAG_List:
            return self.__value[key]

    def __setitem__(self, key, value):
        if self.type_ == TAG_List:
            self.__value[key].__value = value

    def __repr__(self):
        body = (("[\n" + textwrap.indent(",\n".join(repr(x) for x in self.__value), "    ") + "\n]")
                if isinstance(self.__value, list) and self.__value
                else self.__value)
        return f"{self.cls_name}({self.name or 'value'}={body})"

    @property
    def value(self):
        if self.type_ == list:
            tag = TAG_Compound(self.name)
            tag.tags = [x.value for x in self.__value]
            return tag

        if self.type_ == NBTFile:
            x = NBTFile()
            x.name = self.name
            x.tags = [x.value for x in self.__value]
            return x

        if self.type_ == TAG_Compound:
            tag = TAG_Compound(name=self.name)
            tag.tags = [x.value for x in self.__value]
            tag.name = self.name
            return tag

        if self.type_ == TAG_Int_Array:
            tag = TAG_Int_Array(name=self.name)
            tag.value = self.__value
            return tag

        if self.type_ == TAG_List:
            tag = TAG_List(type=self.extra, name=self.name)
            tag.tags = [x.value for x in self.__value]
            tag.name = self.name
            return tag

        return self.type_(value=self.__value, name=self.name)

    @property
    def cls_name(self):
        if self.extra:
            return self.type_.__name__ + f"[{self.extra.__name__}, {self.name}]"
        elif self.name:
            return self.type_.__name__ + f"[{self.name}]"
        else:
            return self.type_.__name__

    @property
    def as_dict(self):
        if issubclass(self.type_, TAG_Compound):
            return {x.name: x.as_dict for x in self.__value}

        if issubclass(self.type_, TAG_List):
            return [x.as_dict for x in self.__value]

        return self.__value


def walk_nbt(x: Any) -> Union[Token, str, int, float, list]:
    if isinstance(x, TAG_Compound):
        return Token(TAG_Compound, x.name, x.tags)
    elif isinstance(x, TAG_List):
        return Token(TAG_List, x.name, x.tags, TAGLIST[x.tagID])
    elif isinstance(x, (str, int, float)):
        return x
    elif isinstance(x, list):
        return [walk_nbt(y) for y in x]
    else:
        return Token(x.__class__, x.name, x.value if x.value is not None else x.tags)


class NBTHandler(object):
    def __init__(self):
        super(NBTHandler, self).__init__()

    def nbt_to_Json(self, nbt_data: Any) -> dict:
        return walk_nbt(nbt_data).as_dict

    def nbt_to_TokenRaw(self, nbt_data: Any) -> Token:
        return walk_nbt(nbt_data)


class PlayerIdentifier(object):
    def __init__(self, uuid, name):
        self.uuid = uuid
        self.name = name


class PlayerData:
    def __init__(self, serverWorkingDir):
        self.playerIds = []
        self.nbt = {}
        self.json = {}
        self.playerCache = {}
        self.playerCache_by_uuid = {}
        self.nbtHandler = NBTHandler()
        self.serverWorkingDir = serverWorkingDir
        self.playerDataDir_path = Path(f"{serverWorkingDir}/world/playerdata")
        self.playerCache_path = Path(f"{serverWorkingDir}/usercache.json")

    def __del__(self):
        self.unload()

    def loadFileIntoMem(self):
        self.playerCache = demjson.decode(open(self.playerCache_path, "r").read())
        self.handlePlayerCache()
        for player_data in os.listdir(self.playerDataDir_path):
            filename = player_data[-4:]
            if filename == ".dat":
                uuid = player_data[0:-4]
                self.nbt[uuid] = NBTFile(f"{self.playerDataDir_path.__str__()}/{player_data}", "rb")
                self.json[uuid] = self.nbtHandler.nbt_to_Json(self.nbt[uuid])

    def handlePlayerCache(self):
        tmp = {}
        tmp_by_uuid = {}
        for player in self.playerCache:
            tmp[player['name']] = player
            tmp_by_uuid[player['uuid']] = player
            self.playerIds.append(PlayerIdentifier(player['uuid'], player['name']))
        self.playerCache = tmp
        self.playerCache_by_uuid = tmp_by_uuid

    def reload(self):
        self.unload()
        self.load()

    def load(self):
        self.loadFileIntoMem()

    def unload(self):
        self.playerIds.clear()
        self.nbt.clear()
        self.json.clear()
        self.playerCache.clear()

    def getNameByUUID(self, uuid: str) -> str:
        return self.playerCache_by_uuid[uuid]['name']

    def getUUIDByName(self, name: str) -> str:
        return self.playerCache[name]['uuid']


class PlayerInfoAPIR:
    def __init__(self, server, serverWorkingDir="./server"):
        self.server = server
        self.workingDir = serverWorkingDir
        self.return_code = -1
        self.saved_flag = False
        self.playerData = PlayerData(serverWorkingDir)

    def __del__(self):
        self.unload()

    def unload(self, code=-1):
        self.playerData.unload()
        if code != -1:
            self.return_code = code

    def load(self):
        self.wait_for_saved()
        self.playerData.load()

    def reload(self):
        self.unload()
        self.load()

    def setFlag(self, fla):
        self.saved_flag = fla

    def wait_for_saved(self):
        self.setFlag(False)
        self.server.execute("save-all")
        while not self.saved_flag:
            pass
        self.setFlag(False)
        self.server.logger.info("Game Saved")

    def getPlayerInfo(self, player: str, NBT=False) -> Union[dict, Any]:
        self.reload()
        if NBT:
            return self.playerData.nbt[self.playerData.getUUIDByName(player)]
        return self.playerData.json[self.playerData.getUUIDByName(player)]

    def getPosition(self, player: str) -> dict:
        p = self.getPlayerInfo(player)['Pos'][0]
        tmp = {"x": p[0], "y": p[1], "z": p[2]}
        return tmp

    def getDimension(self, player: str) -> dict:
        return self.getPlayerInfo(player)['Dimension']

    ### FIND OUT MORE FUNCTION BY YOUSELF :) ###


def createAPI(server, __=False):
    if __:
        if hasattr(server, "PlayerInfoAPIR"):
            return
        server.PlayerInfoAPIR = PlayerInfoAPIR(server)
    else:
        return PlayerInfoAPIR(server)


def on_info(server, info):
    if hasattr(server, "PlayerInfoAPIR"):
        if info.content.startswith("!!PTEST"):
            cmd = info.content.split(" ")
            if info.is_player:
                if len(cmd) > 1:
                    if cmd[1] == "d":
                        server.tell(info.player, json.dumps(server.PlayerInfoAPIR.getDimension(info.player)))
                    elif cmd[1] == "p":
                        server.tell(info.player, json.dumps(server.PlayerInfoAPIR.getPositon(info.player)))
                else:
                    server.tell(info.player, json.dumps(server.PlayerInfoAPIR.getPlayerInfo(info.player)))
            else:
                server.tell(info.player, json.dumps(server.PlayerInfoAPIR.getPlayerInfo(cmd[1])))
        elif info.content == "Saved the game":
            server.PlayerInfoAPIR.setFlag(True)


def on_server_startup(server):
    server.STARTED = True
    createAPI(server, __=True)


def on_load(server, old):
    createAPI(server, __=True)


def on_unload(server):
    if hasattr(server, "PlayerInfoAPIR"):
        server.PlayerInfoAPIR.unload()
        del server.PlayerInfoAPIR


def on_server_stop(server, return_code):
    if hasattr(server, "PlayerInfoAPIR"):
        server.PlayerInfoAPIR.unload(code=return_code)
        del server.PlayerInfoAPIR


def on_mcdr_stop(server):
    if hasattr(server, "PlayerInfoAPIR"):
        server.PlayerInfoAPIR.unload()
        del server.PlayerInfoAPIR

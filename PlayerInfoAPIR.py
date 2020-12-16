from pathlib import Path
import demjson
import os
import textwrap
from typing import Union, Any
from nbt.nbt import NBTFile, TAG_List, TAGLIST, TAG_Compound, TAG_Int_Array


class Token:
    def __init__(self, type_, name, value, extra=None):
        self.__is_set = False
        self.type_ = type_
        self.name = name or ""
        self._value = value if value is None else _to_py(value)
        self.extra = extra

        if self.type_ == TAG_Compound:
            self.keys = [x.name for x in self._value]

        self.__is_set = True

    def __setattr__(self, key, value):
        if key == "_Token__is_set" or not self.__is_set:
            super().__setattr__(key, value)

        elif key == "_value":
            if not isinstance(self._value, (int, str, float, list)):
                self._value._value = value
            else:
                super().__setattr__("_value", value)

        elif hasattr(self, "keys") and key in self.keys:
            item = self[key]
            item._value = value

    def __getattr__(self, item):
        if self.type_ == TAG_Compound and self.__is_set:
            if item in self.keys:
                return self[item]
        super().__getattribute__(item)

    def __getitem__(self, key):
        if self.type_ == TAG_Compound:
            return {x.name: x for x in self._value}[key]
        elif self.type_ == TAG_List:
            return self._value[key]

    def __setitem__(self, key, value):
        if self.type_ == TAG_List:
            self._value[key]._value = value

    @property
    def value(self):
        if self.type_ == list:
            tag = TAG_Compound(self.name)
            tag.tags = [x.value for x in self._value]
            return tag

        if self.type_ == NBTFile:
            x = NBTFile()
            x.name = self.name
            x.tags = [x.value for x in self._value]
            return x

        if self.type_ == TAG_Compound:
            tag = TAG_Compound(name=self.name)
            tag.tags = [x.value for x in self._value]
            tag.name = self.name
            return tag

        if self.type_ == TAG_Int_Array:
            tag = TAG_Int_Array(name=self.name)
            tag.value = self._value
            return tag

        if self.type_ == TAG_List:
            tag = TAG_List(type=self.extra, name=self.name)
            tag.tags = [x.value for x in self._value]
            tag.name = self.name
            return tag

        return self.type_(value=self._value, name=self.name)

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
            return {x.name: x.as_dict for x in self._value}

        if issubclass(self.type_, TAG_List):
            return [x.as_dict for x in self._value]

        return self._value

    def __repr__(self):
        body = (("[\n" + textwrap.indent(",\n".join(repr(x) for x in self._value), "    ") + "\n]") \
                if isinstance(self._value, list) and self._value
                else self._value)
        return f"{self.cls_name}({self.name or 'value'}={body})"

    @property
    def py(self):
        return self.value


def _to_py(x: Any) -> Union[Token, str, int, float, list]:
    if isinstance(x, TAG_Compound):
        return Token(TAG_Compound, x.name, x.tags)
    elif isinstance(x, TAG_List):
        return Token(TAG_List, x.name, x.tags, TAGLIST[x.tagID])
    elif isinstance(x, (str, int, float)):
        return x
    elif isinstance(x, list):
        return [_to_py(y) for y in x]
    else:
        return Token(x.__class__, x.name, x.value if x.value is not None else x.tags)


def nbt_to_json(nbt_data) -> str:
    nbt = nbt_data
    py = _to_py(nbt)
    return py.as_dict


class PlayerInfoAPIR:
    def __init__(self, server, serverWorkingDir="./server"):
        self.server = server
        self.workingDir = serverWorkingDir
        self.return_code = -1
        self.playerDataDir_path = Path(f"{serverWorkingDir}/world/playerdata")
        self.playerCache_path = Path(f"{serverWorkingDir}/usercache.json")
        self.playerCache = None
        self.playerData_nbt = {}
        self.playerData_json = {}
        self.saved_flag = False

    def __del__(self):
        self.unload()

    def unload(self, code=-1):
        self.playerCache = None
        self.playerData_nbt.clear()
        self.playerData_json.clear()
        self.saved_flag = False
        if code != -1:
            self.return_code = code

    def load(self):
        self.server.execute("save-all")
        self.loadFileIntoMem()
        self.NBT2Json()

    def reload(self):
        self.unload()
        self.load()

    def loadFileIntoMem(self):
        self.playerCache = demjson.decode(open(self.playerCache_path, "r").read())
        self.indexPlayerCache()
        for player_data in os.listdir(self.playerDataDir_path):
            if player_data[-4:] == ".dat":
                self.playerData_nbt[player_data[0:-4]] = \
                    NBTFile(f"{self.playerDataDir_path.__str__()}/{player_data}", "rb")

    def indexPlayerCache(self):
        tmp = {}
        for player in self.playerCache:
            tmp[player['name']] = player
        self.playerCache = tmp

    def NBT2Json(self):
        tmp = {}
        for playerUUID in self.playerData_nbt.keys():
            tmp[playerUUID] = nbt_to_json(self.playerData_nbt[playerUUID])
        self.playerData_json = tmp

    def getUUID(self, playerId):
        return self.playerCache[playerId]["uuid"]

    def getPlayerInfo(self, player, NBT=False):
        self.reload()
        while not self.saved_flag:
            pass
        self.server.logger.info("Game Saved, Ready To Read")
        self.saved_flag = False
        if NBT:
            return self.playerData_nbt[self.getUUID(player)]
        return self.playerData_json[self.getUUID(player)]


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
                print(server.PlayerInfoAPIR.getPlayerInfo(info.player))
            else:
                print(server.PlayerInfoAPIR.getPlayerInfo(cmd[1]))
        elif info.content == "Saved the game":
            server.PlayerInfoAPIR.saved_flag = True


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

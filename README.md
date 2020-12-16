# PlayerInfoAPIR
使用NBT文件重写的PlayerInfoAPI

## 安装:

下载 `PlayerInfoAPIR.py` , 移动至 `plugins` 目录

## 使用:

`PlayerInfoAPIR` 会在MCDR启动时自动被加载至 `server` 动态类中，可以使用 `server.PlayerInfoAPIR.getPlayerInfo` 来调用它

[示例插件]: https://github.com/ixiaohei-sakura/PlayerInfoAPIR/blob/master/demoPlugin.py	"插件"

##### 下面附上表格:

| 属性        | 名称                                                   | 描述                                                         |
| ----------- | ------------------------------------------------------ | ------------------------------------------------------------ |
| 函数        | `createAPI(server)`                                    | 返回一个API类实例                                            |
| 类- Class   | `PlayerInfoAPIR(server, serverWorkingDir="./server")`  | API类                                                        |
| API成员函数 | `PlayerInfoAPIR.getUUID(player: str)`                  | 获取对应id玩家的uuid                                         |
| API成员函数 | `PlayerInfoAPIR.getPlayerInfo(player: str, NBT=False)` | 返回这个玩家所有属性的dict字典, 当NBT参数为`True`时将会返回此玩家的nbt属性值 |



## 特点:

* 可以获取不在线玩家(上过至少一次线)的数据
* 快速，终端不刷屏

**可能存在的缺点:**

* ⚠️注意，API在被调用时会保存一次世界，介意者慎用
* 可能造成瞬间的卡顿
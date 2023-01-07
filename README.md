# Hpool2nossd

- 完成Hpool plots 到 Nossd fpt的转换
- Nossd和Hpool需配置成服务
- pool2nossd也需配置为服务
- Nossd和Hpool服务调度(默认Nossd转换磁盘数量3)
    - 已经设定磁盘转换
        - 1.检测Nossd服务转换情况，如果Nossd转换满磁盘
        - 2.停止Hpool服务(由于Hpool minner独占磁盘,需停止后才能删除plots)
        - 3.删除一定数量的plots
        - 4.启动Hpool服务
        - 5.继续检测Nossd服务,重复1-4
    - 新磁盘设定
        - 1.检测磁盘现存Hpool plots目录是否为空 且 Nossd fpt目录是否填满
        - 2.如果满足1情况，则停止Nossd服务
        - 3.从待转换的Hpool plots磁盘中选择新的3个磁盘作为新转换目录
        - 4.更新Nossd "start.sh" 脚本
        - 5.停止Hpool服务
        - 6.删除新转换目录一定数量的plots
        - 7.启动Hpool服务
        - 8.启动Nossd服务
        - 9.继续进入`已设定磁盘转换`

    - 循环监控重复 `已设定磁盘转换` `新磁盘设定`
    - 程序退出，当待转换Hpool plots磁盘全部转换完成

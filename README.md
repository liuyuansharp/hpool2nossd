# Hpool转Nossd自动化工具

## 特点
- 可支持自定义fpt/spt优先级
- 可支持自定义每次删除图数量
- 开机启动，无人值守
## 简介
- 完成Hpool plots 到 Nossd fpt的转换
- Nossd、Hpool、Hpool2nossd需配置成服务
- Nossd和Hpool服务调度
    - 初始状态设定
        - 1.获取初始磁盘列表
        - 2.获取初始磁盘状态
        - 3.判断当前磁盘状态
        - 4.停止Nossd服务
        - 5.初始化Nossd脚本
        - 6.启动Nossd服务
    - 已设定磁盘转换
        - 1.检测磁盘转换情况，如果Nossd转换满磁盘
        - 2.停止Hpool服务(由于Hpool minner独占磁盘,需停止后才能删除plots)
        - 3.删除一定数量的plots
        - 4.启动Hpool服务
        - 5.停止Nossd服务
        - 6.更新Nossd脚本
        - 7.启动Nossd服务
        - 8.继续检测Nossd服务,重复1-7
    - 循环监控重复 `已设定磁盘转换` 
    - 程序退出，当待转换Hpool plots磁盘全部转换完成
## 使用方法

### 获取hpool2nossd.py
```
#安装python3
su root
apt install python3

#下载
git clone https://github.com/liuyuansharp/hpool2nossd.git
```
### 配置hpool2nossd输入
``` python
#配置hpool2nossd.py 47-88行
###################配置区域开始###################
#是否fpt文件优先
self.fpt_priority = False
#每次删除hpool图数量
self.delete_plots_num_per_time = 2

#磁盘挂载根目录
self.drive_root_path = Path("/srv/")
#磁盘文件夹标识（用于排除磁盘挂载根目录下排除无效目录，可为填""，则不作排除）
self.drive_character = "disk"

#hpool图目录名
self.plots_dir = "chiapp-files"
#nossd图目录名
self.nossd_dir = "nossd"
#hpool服务名
self.hpool_service = "hpoolpp"
#nossd服务名
self.nossd_service = "nossd"

#nossd安装文件目录
self.nossd_path = Path("/root/install/nossd-1.2/")
#nossd脚本名
self.nossd_start_sh_name = "start.sh"

#nossd压缩等级
self.nossd_type = 5
#nossd机器名
self.nossd_name = "bsh_001"
#nossd收益地址
self.nossd_address = "xch1m49h6ny95xgs5a3p2wg6ghnr3vejsqq2pwklq9ae8kg8wgkfujcs26djuq"
#nossd临时文件磁盘
self.nossd_tmp_drive_paths = \
    [
        "/srv/dev-disk-by-uuid-9802c526-c5e2-44a4-9e29-b7e1b7b805a0",
        "/srv/dev-disk-by-uuid-ffeb0e19-8f2a-453a-abec-9aa7884c1124",
        "/srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01"
    ]
###################配置区域结束####################

```

### 配置hpool2nossd服务
```
# 必须是root用户
# sudo su

# 创建systemd服务，根据hpool2nossd.py位置 配置以下路径
cat > /lib/systemd/system/hpool2nossd.service <<EOF
[Unit]
Description=hpool2nossd
After=multi-user.target
StartLimitIntervalSec=0

[Service]
Type=forking
ExecStart=/bin/bash -c "/usr/bin/python3 /root/install/hpool2nossd/hpool2nossd.py &"
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Restart=always
RestartSec=1
TimeoutStartSec=30
User=root

[Install]
WantedBy=multi-user.target
EOF

# 设置开机启动，并启动该服务（按需）
systemctl daemon-reload
systemctl enable hpool2nossd

systemctl start hpool2nossd
```
### 检查记录
```
journalctl -u hpool2nossd.service -f
```

```
#示例

1月 10 23:18:18 harvester2 bash[2015151]: status: plotting
1月 10 23:18:18 harvester2 bash[2015151]: drive: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01
1月 10 23:18:18 harvester2 bash[2015151]: drive info: [total_gb/used_gb/free_gb] : [16696/15785/910]
1月 10 23:18:18 harvester2 bash[2015151]: nossd dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/nossd
1月 10 23:18:18 harvester2 bash[2015151]: nossd info: fpts_n: 77 spts_n: 1
1月 10 23:18:18 harvester2 bash[2015151]: plots dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files
1月 10 23:18:18 harvester2 bash[2015151]: plots info: plots_n: 95
1月 10 23:18:18 harvester2 bash[2015151]: waitting 300 s ,check drives status again....
1月 10 23:23:19 harvester2 bash[2015151]: check drives status....
1月 10 23:23:19 harvester2 bash[2015151]: status: plotting
1月 10 23:23:19 harvester2 bash[2015151]: drive: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01
1月 10 23:23:19 harvester2 bash[2015151]: drive info: [total_gb/used_gb/free_gb] : [16696/15785/910]
1月 10 23:23:19 harvester2 bash[2015151]: nossd dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/nossd
1月 10 23:23:19 harvester2 bash[2015151]: nossd info: fpts_n: 77 spts_n: 1
1月 10 23:23:19 harvester2 bash[2015151]: plots dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files
1月 10 23:23:19 harvester2 bash[2015151]: plots info: plots_n: 95
1月 10 23:23:19 harvester2 bash[2015151]: waitting 300 s ,check drives status again....
```

### 配置hpool服务
```
# 必须是root用户
# sudo su

# 创建systemd服务，根据hpool minner位置 配置以下路径
cat > /lib/systemd/system/hpoolpp.service <<EOF
[Unit]
Description=hpoolpp
After=multi-user.target
StartLimitIntervalSec=0

[Service]
Type=forking
ExecStart=/bin/bash -c "/home/chiapp/linux/hpool-miner-chia-pp -config /home/chiapp/config.yaml &" 
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Restart=always
RestartSec=1
TimeoutStartSec=30
User=root

[Install]
WantedBy=multi-user.target
EOF

# 设置开机启动，并启动该服务
systemctl daemon-reload
systemctl enable hpoolpp

systemctl start hpoolpp
```

### 检查记录
```
journalctl -u hpoolpp.service -f
```

### 配置nossd服务
```
# 必须是root用户
# sudo su

# 创建systemd服务，根据nossd minner位置 配置以下启动脚本路径
cat > /lib/systemd/system/nossd.service <<EOF
[Unit]
Description=nossd
After=multi-user.target
StartLimitIntervalSec=0

[Service]
Type=forking
ExecStart=/bin/bash -c "/root/install/nossd-1.2/start.sh &"  
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Restart=always
RestartSec=1
TimeoutStartSec=30
User=root

[Install]
WantedBy=multi-user.target
EOF

# 设置开机启动，并启动该服务
systemctl daemon-reload
systemctl enable nossd

systemctl start nossd
```

### 检查记录
```
journalctl -u nossd.service -f
```
